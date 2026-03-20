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
import {isNonNormalState} from 'src/resources/RepositoryResource';

export default function TagExpiration(props: TagExpirationProps) {
  const [isEditExpirationModalOpen, setIsEditExpirationModalOpen] =
    useState(false);
  const quayConfig = useQuayConfig();
  const canImmutableTagsExpire =
    quayConfig?.config?.FEATURE_IMMUTABLE_TAGS_CAN_EXPIRE ?? false;

  const isImmutableAndCannotExpire = props.immutable && !canImmutableTagsExpire;
  const isNonNormalRepo = isNonNormalState(props.repoState);

  let message: ReactElement = null;
  // If immutable and config disallows expiration, show "Never" even if expiration is set
  if (isNullOrUndefined(props.expiration) || isImmutableAndCannotExpire) {
    message = (
      <span
        style={{
          color: '#aaa',
          ...(isImmutableAndCannotExpire || isNonNormalRepo
            ? {}
            : {textDecoration: 'underline dotted'}),
        }}
      >
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

    const underlineStyle = isNonNormalRepo
      ? {}
      : {textDecoration: 'underline dotted'};
    if (timeDifferenceDays <= 7) {
      message = (
        <span style={{color: '#f77454', ...underlineStyle}}>
          <ExclamationTriangleIcon /> {timeDifferenceHumanFormat}
        </span>
      );
    } else if (timeDifferenceDays > 7 && timeDifferenceDays <= 31) {
      message = (
        <span style={{color: '#fca657', ...underlineStyle}}>
          <ExclamationTriangleIcon /> {timeDifferenceHumanFormat}
        </span>
      );
    } else if (timeDifferenceDays > 31) {
      message = (
        <span style={{color: '#2fc98e', ...underlineStyle}}>
          <OutlinedClockIcon /> {timeDifferenceHumanFormat}
        </span>
      );
    }
  }

  const showNever =
    isNullOrUndefined(props.expiration) || isImmutableAndCannotExpire;

  const isReadOnly = isImmutableAndCannotExpire || isNonNormalRepo;

  const renderExpirationContent = () => {
    if (showNever && isReadOnly) {
      return (
        <Tooltip
          content={
            isNonNormalRepo
              ? 'Tag expiration cannot be modified on this repository'
              : 'Immutable tags cannot have expiration'
          }
        >
          <span
            tabIndex={0}
            aria-label={
              isNonNormalRepo
                ? 'Tag expiration cannot be modified'
                : 'Immutable tags cannot expire'
            }
          >
            {message}
          </span>
        </Tooltip>
      );
    }
    if (showNever) {
      return (
        <a onClick={() => setIsEditExpirationModalOpen(true)}>{message}</a>
      );
    }
    if (isNonNormalRepo) {
      return (
        <Tooltip
          content={formatDate(new Date(props.expiration).getTime() / 1000)}
        >
          <span>{message}</span>
        </Tooltip>
      );
    }
    return (
      <Tooltip
        content={formatDate(new Date(props.expiration).getTime() / 1000)}
      >
        <a onClick={() => setIsEditExpirationModalOpen(true)}>{message}</a>
      </Tooltip>
    );
  };

  return (
    <>
      {renderExpirationContent()}
      {!isNonNormalRepo && (
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
      )}
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
  repoState?: string | null;
}
