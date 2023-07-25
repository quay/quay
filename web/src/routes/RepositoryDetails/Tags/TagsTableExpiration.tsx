import { ExclamationTriangleIcon, OutlinedClockIcon } from "@patternfly/react-icons";
import { formatDate, humanizeTimeForExpiry, isNullOrUndefined } from "src/libs/utils";
import { Tooltip } from '@patternfly/react-core';
import { ReactElement, useState } from "react";
import EditExpirationModal from "./TagsActionsEditExpirationModal";

export default function TagExpiration(props: TagExpirationProps) {
    const [isEditExpirationModalOpen, setIsEditExpirationModalOpen] = useState(false);

    let message: ReactElement = null;
    if (isNullOrUndefined(props.expiration)) {
        message =  (<span style={{ color: '#aaa', textDecoration: 'underline dotted' }}>Never</span>);
    } else {
        const timeDifferenceSeconds: number = (new Date(props.expiration).getTime() - new Date().getTime()) / 1000;
        const timeDifferenceHumanFormat: string = humanizeTimeForExpiry(timeDifferenceSeconds)
        const timeDifferenceDays: number = timeDifferenceSeconds / 60 / 60 / 24;
    
        if (timeDifferenceDays <= 7) {
            message = (<span style={{ color: '#f77454', textDecoration: 'underline dotted' }}><ExclamationTriangleIcon /> {timeDifferenceHumanFormat}</span>)
        } else if (timeDifferenceDays > 7 && timeDifferenceDays <= 31) {
            message = (<span style={{ color: '#fca657', textDecoration: 'underline dotted' }}><ExclamationTriangleIcon /> {timeDifferenceHumanFormat}</span>)
        } else if (timeDifferenceDays > 31) {
            message = (<span style={{ color: '#2fc98e', textDecoration: 'underline dotted' }}><OutlinedClockIcon /> {timeDifferenceHumanFormat}</span>)
        }
    }

    return (
        <>
            <Tooltip content={formatDate(new Date(props.expiration).getTime() / 1000)}>
                <a onClick={() => setIsEditExpirationModalOpen(true)}>
                    {message}
                </a>
            </Tooltip>
            <EditExpirationModal
                org={props.org}
                repo={props.repo}
                isOpen={isEditExpirationModalOpen}
                setIsOpen={setIsEditExpirationModalOpen}
                tags={[props.tag]}
                loadTags={props.loadTags}
                expiration={props.expiration}
            />
        </>
    )
}

interface TagExpirationProps {
    org: string;
    repo: string;
    expiration: string | null;
    tag: string;
    loadTags: () => void;
}
