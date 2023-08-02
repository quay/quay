import {
    Label as ImageLabel,
} from 'src/resources/TagResource';
import { Button, DescriptionList, DescriptionListDescription, DescriptionListGroup, DescriptionListTerm, Label, Skeleton} from '@patternfly/react-core';
import './Labels.css';
import { useLabels } from 'src/hooks/UseTagLabels';
import { useEffect, useState } from 'react';
import Conditional from '../empty/Conditional';
import { useAlerts } from 'src/hooks/UseAlerts';
import { AlertVariant } from 'src/atoms/AlertState';
import EditableLabel from './EditableLabel';

export default function EditableLabels(props: EditableLabelsProps) {
    const {
        labels,
        setLabels,
        initialLabels,
        loading,
        error,
        createLabels,
        successCreatingLabels,
        errorCreatingLabels,
        errorCreatingLabelsDetails,
        loadingCreateLabels,
        deleteLabels,
        successDeletingLabels,
        errorDeletingLabels,
        errorDeletingLabelsDetails,
        loadingDeleteLabels,
    } = useLabels(props.org, props.repo, props.digest);
    const [newLabel, setNewLabel] = useState<string>('');
    const [invalidNewLabel, setInvalidNewLabel] = useState<string>(null);
    const { addAlert } = useAlerts();
    const loadingLabelChanges: boolean = loadingCreateLabels || loadingDeleteLabels;
    const readonlyLabels = labels.filter((label: ImageLabel) => label.source_type !== 'api');
    const mutableLabels = labels.filter((label: ImageLabel) => label.source_type === 'api');

    if (error) {
        return <>Unable to get labels</>;
    }
    if (loading) {
        return <Skeleton width="100%" />;
    }

    useEffect(() => {
        if (successCreatingLabels) {
            addAlert({ variant: AlertVariant.Success, title: `Created labels successfully` });
        }
        if (errorCreatingLabels) {
            let errorCreatingLabelsMessage = (<>{Array.from(errorCreatingLabelsDetails.getErrors()).map(([label, error]) => (<p key={label}>Could not create label {label}: {error.error.message}</p>))}</>)
            addAlert({ variant: AlertVariant.Failure, title: `Could not create labels`, message: errorCreatingLabelsMessage });
        }
        if (successDeletingLabels) {
            addAlert({ variant: AlertVariant.Success, title: `Deleted labels successfully` });
        }
        if (errorDeletingLabels) {
            let errorDeletingLabelsMessage = (<>{Array.from(errorDeletingLabelsDetails.getErrors()).map(([label, error]) => (<p key={label}>Could not delete label {label}: {error.error.message}</p>))}</>)
            addAlert({ variant: AlertVariant.Failure, title: `Could not delete labels`, message: errorDeletingLabelsMessage });
        }
        if ((successCreatingLabels || errorCreatingLabels || successDeletingLabels || errorDeletingLabels) && !loadingLabelChanges) {
            props.onComplete();
        }
    }, [successCreatingLabels, errorCreatingLabels, successDeletingLabels, errorDeletingLabels]);

    const onEditComplete = (newLabel: string) => {
        if(newLabel === '') {
            setNewLabel('');
            setInvalidNewLabel(null);
            return;
        }
        let invalidMessage: string = null;
        let key: string = null;
        let value: string = null;
        const keyValue: string[] = newLabel.split('=');
        if (keyValue.length === 2) {
            key = keyValue[0].trim();
            value = keyValue[1].trim();
            if (key === "" || !/^[0-9A-Za-z/\-_.]+$/.test(key)) {
                invalidMessage = 'Invalid label format, key must match ^[0-9A-Za-z/\\-_.]+=.+$'
            }
            if (value === "" || !/^[0-9A-Za-z/\-_.]+$/.test(value)) {
                invalidMessage = 'Invalid label format, value must match ^[0-9A-Za-z/\\-_.]+=.+$';
            }
        } else {
            invalidMessage = 'Invalid label format, must be key value separated by ='
        }

        if (labels.some(l => l.key === key && l.value === value)) {
            invalidMessage = 'Key value already exists'
        }

        if (invalidMessage === null) {
            setNewLabel('');
            const newLabelObj: ImageLabel = { id: `${key}=${value}`, key, value, source_type: 'api', media_type: null };
            setLabels(prev => [...prev, newLabelObj])
            setInvalidNewLabel(null);
        } else {
            setInvalidNewLabel(invalidMessage);
            setNewLabel(newLabel);
        }
    }

    const removeLabel = (label: ImageLabel) => {
        setLabels(prev => prev.filter(l => l.id !== label.id))
    }

    const saveLabels = () => {
        const [addedLabels, deletedLabels] = filterLabels(initialLabels, labels);
        if (addedLabels.length > 0) {
            createLabels(addedLabels);
        }
        if (deletedLabels.length > 0) {
            deleteLabels(deletedLabels);
        }
    }

    const isSaveButtonDisabled = () => {
        const [addedLabels, deletedLabels] = filterLabels(initialLabels, labels);
        return (addedLabels.length === 0 && deletedLabels.length === 0);
    }

    const filterLabels = (initialLabels: ImageLabel[], updatedLabels: ImageLabel[]) => {
        const addedLabels: ImageLabel[] = updatedLabels.filter(updatedLabel => !initialLabels.some(intitialLabel => intitialLabel.key===updatedLabel.key && intitialLabel.value===updatedLabel.value));
        const deletedLabels: ImageLabel[] = initialLabels.filter(intitialLabel => !updatedLabels.some(updatedLabel => intitialLabel.key===updatedLabel.key && intitialLabel.value===updatedLabel.value));
        return [addedLabels, deletedLabels];
    }

    return (<>
        <DescriptionList>
            <DescriptionListGroup>
                <DescriptionListTerm>Read-only labels</DescriptionListTerm>
                <DescriptionListDescription id='readonly-labels'>
                    {readonlyLabels?.length === 0 ? "No labels found" : readonlyLabels.map((label: ImageLabel) => (
                        <>
                            <Label key={label.key} className="label">
                                <span className="label-content">
                                    {label.key} = {label.value}
                                </span>
                            </Label>{' '}
                        </>
                    ))}
                </DescriptionListDescription>
            </DescriptionListGroup>
            <DescriptionListGroup>
                <DescriptionListTerm>Mutable labels</DescriptionListTerm>
                <DescriptionListDescription id='mutable-labels'>
                    {mutableLabels?.map((label: ImageLabel) => (
                        <Label key={label.id} className="label" onClose={() => { removeLabel(label) }}>
                            <span className="label-content">
                                {label.key}={label.value}
                            </span>
                        </Label>
                    ))}
                    <EditableLabel
                        value={newLabel}
                        setValue={setNewLabel}
                        onEditComplete={onEditComplete}
                        invalid={invalidNewLabel !== null}
                    />
                    <Conditional if={invalidNewLabel !== null}>
                        <div style={{ color: 'red' }}>
                            {invalidNewLabel}
                        </div>
                    </Conditional>
                </DescriptionListDescription>
            </DescriptionListGroup>
        </DescriptionList>
        <br />
        <Button
            key="cancel"
            variant="primary"
            onClick={props.onComplete}
        >
            Cancel
        </Button>{' '}
        <Button
            key="modal-action-button"
            variant="primary"
            onClick={saveLabels}
            isDisabled={isSaveButtonDisabled()}
        >
            Save Labels
        </Button>
    </>)
}

interface EditableLabelsProps {
    org: string;
    repo: string;
    digest: string;
    onComplete?: () => void;
}
