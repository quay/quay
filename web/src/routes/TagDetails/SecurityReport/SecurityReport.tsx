import {Skeleton} from '@patternfly/react-core';
import RequestError from 'src/components/errors/RequestError';
import {useManifestSecurity} from 'src/hooks/UseManifestSecurity';
import {addDisplayError} from 'src/resources/ErrorHandling';
import {SecurityReportChart} from './SecurityReportChart';
import {
  FailedState,
  QueuedState,
  UnsupportedState,
} from './SecurityReportScanStates';
import SecurityReportTable from './SecurityReportTable';

export interface SecurityReportProps {
  org: string;
  repo: string;
  digest: string;
}

export default function SecurityReport(props: SecurityReportProps) {
  const {
    securityDetails,
    isSecurityDetailsLoading,
    isSecurityDetailsError,
    securityDetailsError,
  } = useManifestSecurity(
    props.org,
    props.repo,
    props.digest,
    props.digest !== '',
  );

  if (isSecurityDetailsLoading) {
    return <Skeleton width="50%"></Skeleton>;
  }

  if (isSecurityDetailsError) {
    return (
      <RequestError
        message={addDisplayError(
          securityDetailsError.toString(),
          securityDetailsError as Error,
        )}
      />
    );
  }

  // Return correct messages for the different scan states
  if (securityDetails?.status === 'queued') {
    return <QueuedState />;
  } else if (securityDetails?.status === 'failed') {
    return <FailedState />;
  } else if (
    securityDetails?.status === 'unsupported' ||
    securityDetails?.data?.Layer?.Features?.length == 0
  ) {
    return <UnsupportedState />;
  }

  // Set features to a default of null to distinuish between a completed API call and one that is in progress
  const features = securityDetails ? securityDetails.data.Layer.Features : null;
  return (
    <>
      <SecurityReportChart features={features} />
      <hr />
      <SecurityReportTable features={features} />
    </>
  );
}
