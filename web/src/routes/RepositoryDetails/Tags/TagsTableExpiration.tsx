import {
  ExclamationTriangleIcon,
  OutlinedClockIcon,
} from '@patternfly/react-icons';
import {
  formatDate,
  humanizeTimeForExpiry,
  isNullOrUndefined,
} from 'src/libs/utils';
import {Tooltip} from '@patternfly/react-core';
import {ReactElement, useState} from 'react';
import EditExpirationModal from './TagsActionsEditExpirationModal';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';

export default function TagExpiration(props: TagExpirationProps) {
  const [isEditExpirationModalOpen, setIsEditExpirationModalOpen] =
    useState(false);
  const quayConfig = useQuayConfig();
  const canImmutableTagsExpire =
    quayConfig?.config?.FEATURE_IMMUTABLE_TAGS_CAN_EXPIRE ?? false;

  let message: ReactElement = null;
  // If immutable and config disallows expiration, show "Never" even if expiration is set
  if (
    isNullOrUndefined(props.expiration) ||
    (props.immutable && !canImmutableTagsExpire)
  ) {
    message = (
      <span style={{color: '#aaa', textDecoration: 'underline dotted'}}>
        Never
      </span>
    );
  } else {
    const timeDifferenceSeconds: number =
      (new Date(props.expiration).getTime() - new Date().getTime()) / 1000;
    const timeDifferenceHumanFormat: string = humanizeTimeForExpiry(
      timeDifferenceSeconds,
    );
    const timeDifferenceDays: number = timeDifferenceSeconds / 60 / 60 / 24;

    if (timeDifferenceDays <= 7) {
      message = (
        <span style={{color: '#f77454', textDecoration: 'underline dotted'}}>
          <ExclamationTriangleIcon /> {timeDifferenceHumanFormat}
        </span>
      );
    } else if (timeDifferenceDays > 7 && timeDifferenceDays <= 31) {
      message = (
        <span style={{color: '#fca657', textDecoration: 'underline dotted'}}>
          <ExclamationTriangleIcon /> {timeDifferenceHumanFormat}
        </span>
      );
    } else if (timeDifferenceDays > 31) {
      message = (
        <span style={{color: '#2fc98e', textDecoration: 'underline dotted'}}>
          <OutlinedClockIcon /> {timeDifferenceHumanFormat}
        </span>
      );
    }
  }

  const showNever =
    isNullOrUndefined(props.expiration) ||
    (props.immutable && !canImmutableTagsExpire);

  return (
    <>
      {showNever ? (
        <a onClick={() => setIsEditExpirationModalOpen(true)}>{message}</a>
      ) : (
        <Tooltip
          content={formatDate(new Date(props.expiration).getTime() / 1000)}
        >
          <a onClick={() => setIsEditExpirationModalOpen(true)}>{message}</a>
        </Tooltip>
      )}
      <EditExpirationModal
        org={props.org}
        repo={props.repo}
        isOpen={isEditExpirationModalOpen}
        setIsOpen={setIsEditExpirationModalOpen}
        tags={[props.tag]}
        loadTags={props.loadTags}
        expiration={props.expiration}
        immutableTags={
          canImmutableTagsExpire ? [] : props.immutable ? [props.tag] : []
        }
      />
    </>
  );
}

interface TagExpirationProps {
  org: string;
  repo: string;
  expiration: string | null;
  tag: string;
  loadTags: () => void;
  immutable?: boolean;
}
