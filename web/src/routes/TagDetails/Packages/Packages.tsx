import {PackagesChart} from './PackagesChart';
import PackagesTable from './PackagesTable';
import {useRecoilState, useRecoilValue} from 'recoil';
import {
  SecurityDetailsErrorState,
  SecurityDetailsState,
} from 'src/atoms/SecurityDetailsState';
import {isErrorString} from 'src/resources/ErrorHandling';
import RequestError from 'src/components/errors/RequestError';
import {
  QueuedState,
  FailedState,
  UnsupportedState,
} from 'src/routes/TagDetails/SecurityReport/SecurityReportScanStates';

export function Packages() {
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

  // Set features to a default of null to distinguish between a completed API call and one that is in progress
  const features = data ? data.data.Layer.Features : null;
  return (
    <>
      <PackagesChart features={features} />
      <hr />
      <PackagesTable features={features} />
    </>
  );
}
