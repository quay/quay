import { Button, Modal, ModalVariant, TextInput, Title } from "@patternfly/react-core";
import { useEffect, useState } from "react";
import { AlertVariant } from "src/atoms/AlertState";
import { useAlerts } from "src/hooks/UseAlerts";
import { useTags } from "src/hooks/UseTags";


export default function AddTagModal(props: AddTagModalProps){
    const [value, setValue] = useState('');
    const {addAlert} = useAlerts();
    const {createTag, successCreateTag, errorCreateTag} = useTags(props.org, props.repo);

    useEffect(() => { 
        if(successCreateTag){
            addAlert({variant: AlertVariant.Success, title: `Successfully created tag ${value}`});
            setValue('');
            props.loadTags();
            props.setIsOpen(false);
        }
    }, [successCreateTag]);

    useEffect(() => { 
        if(errorCreateTag){
            addAlert({variant: AlertVariant.Failure, title: `Could not create tag ${value}`});
            setValue('')
            props.setIsOpen(false)
        }
    }, [errorCreateTag]);

    return (
        <>
            <Modal
                id="add-tag-modal"
                header={(<Title headingLevel="h2">Add tag to manifest {props.manifest.substring(0, 19)}</Title>)}
                aria-label="Add tag modal"
                isOpen={props.isOpen}
                onClose={() => props.setIsOpen(false)}
                variant={ModalVariant.small}
                actions={[
                    <Button
                    key="cancel"
                    variant="primary"
                    onClick={() => props.setIsOpen(false)}
                >
                    Cancel
                </Button>,
                <Button
                    key="modal-action-button"
                    variant="primary"
                    onClick={()=>{createTag({tag: value, manifest: props.manifest})}}
                >
                    Create tag
                </Button>,
                ]}
            >
                <TextInput 
                    value={value} 
                    type="text" 
                    onChange={value => setValue(value)} 
                    aria-label="new tag name"
                    placeholder="New tag name"
                />
            </Modal>
        </>
    )
}

interface AddTagModalProps {
    org: string;
    repo: string;
    isOpen: boolean;
    manifest: string;
    setIsOpen: (open: boolean) => void;
    loadTags: () => void;
}
