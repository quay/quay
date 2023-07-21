import {
    Label as ImageLabel,
} from 'src/resources/TagResource';
import { Label, Skeleton } from "@patternfly/react-core";
import { useLabels } from "src/hooks/UseTagLabels";

export default function ReadOnlyLabels(props: ReadOnlyLabelsProps) {
    const {
        labels,
        loading,
        error,
    } = useLabels(props.org, props.repo, props.digest);

    if (error) {
        return <>Unable to get labels</>;
    }
    if (loading) {
        return <Skeleton width="100%" />;
    }

    return labels?.length === 0 ? <>No labels found</> :
        (
            <>
                {labels.map((label: ImageLabel) => (
                    <>
                        <Label key={label.key} className="label">
                            <span className="label-content">
                                {label.key} = {label.value}
                            </span>
                        </Label>{' '}
                    </>
                ))}
            </>
        );
}

interface ReadOnlyLabelsProps {
    org: string;
    repo: string;
    digest: string;
}
