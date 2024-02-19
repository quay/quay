import {useState} from 'react';
import {useRecoilValue} from 'recoil';
import {
  SecurityDetailsErrorState,
  SecurityDetailsState,
} from 'src/atoms/SecurityDetailsState';
import RequestError from 'src/components/errors/RequestError';
import {isErrorString} from 'src/resources/ErrorHandling';
import {Tag} from 'src/resources/TagResource';
import {VulnerabilitySuppressionsModal} from 'src/components/modals/VulnerabilitySuppressionsModal';
import {SecurityReportChart} from './SecurityReportChart';
import {
  FailedState,
  QueuedState,
  UnsupportedState,
} from './SecurityReportScanStates';
import SecurityReportTable from './SecurityReportTable';

export default function SecurityReport(props: SecurityReportProps) {
  const [isSuppressionModalOpen, setIsSuppressionModalOpen] = useState(false);
  const data = useRecoilValue(SecurityDetailsState);
  const error = useRecoilValue(SecurityDetailsErrorState);

  if (isErrorString(error)) {
    return <RequestError message={error} />;
  }

  // Return correct messages for the different scan states
  if (data && data.status === 'queued') {
    return <QueuedState />;
  } else if (data && data.status === 'failed') {
    return <FailedState />;
  } else if (data && data.status === 'unsupported') {
    return <UnsupportedState />;
  }

  // Set features to a default of null to distinuish between a completed API call and one that is in progress
  const features = data ? data.data.Layer.Features : null;
  return (
    <>
      <SecurityReportChart features={features} />
      <hr />
      <SecurityReportTable
        features={features}
        setSuppressionModalOpen={setIsSuppressionModalOpen}
      />

      {isSuppressionModalOpen && (
        <VulnerabilitySuppressionsModal
          isOpen={isSuppressionModalOpen}
          setIsOpen={setIsSuppressionModalOpen}
          org={props.org}
          repo={props.repo}
          digest={props.digest}
          tag={props.tag}
        />
      )}
    </>
  );
}

type SecurityReportProps = {
  tag: Tag;
  org: string;
  repo: string;
  digest: string;
};
