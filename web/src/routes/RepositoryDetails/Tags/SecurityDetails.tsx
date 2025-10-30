import {useMemo} from 'react';
import {useSecurityDetails} from 'src/hooks/UseSecurityDetails';
import {Link, useLocation} from 'react-router-dom';
import {Skeleton} from '@patternfly/react-core';
import {getTagDetailPath} from 'src/routes/NavigationPath';
import {TabIndex} from 'src/routes/TagDetails/Types';
import {VulnerabilitySeverity} from 'src/resources/TagResource';
import {
  ExclamationTriangleIcon,
  CheckCircleIcon,
} from '@patternfly/react-icons';
import {getSeverityColor} from 'src/libs/utils';
import {isErrorString} from 'src/resources/ErrorHandling';

enum Variant {
  condensed = 'condensed',
  full = 'full',
}

export default function SecurityDetails(props: SecurityDetailsProps) {
  const {
    data: securityDetails,
    error,
    isLoading,
  } = useSecurityDetails(props.org, props.repo, props.digest);
  const location = useLocation();

  const severityOrder = [
    VulnerabilitySeverity.Critical,
    VulnerabilitySeverity.High,
    VulnerabilitySeverity.Medium,
    VulnerabilitySeverity.Low,
    VulnerabilitySeverity.Negligible,
    VulnerabilitySeverity.Unknown,
  ];

  // Calculate vulnerability counts from security details
  const vulnCount = useMemo(() => {
    const vulns = new Map<VulnerabilitySeverity, number>();
    if (securityDetails?.data) {
      for (const feature of securityDetails.data.Layer.Features) {
        if (feature.Vulnerabilities) {
          for (const vuln of feature.Vulnerabilities) {
            if (vuln.Severity in VulnerabilitySeverity) {
              if (vulns.has(vuln.Severity)) {
                vulns.set(vuln.Severity, vulns.get(vuln.Severity) + 1);
              } else {
                vulns.set(vuln.Severity, 1);
              }
            }
          }
        }
      }
    }
    return vulns;
  }, [securityDetails]);

  const hasFeatures =
    securityDetails?.data?.Layer?.Features?.length > 0 || false;
  const status = securityDetails?.status;

  const getHighestSeverity = () => {
    for (const severity of severityOrder) {
      if (vulnCount.get(severity) != null && vulnCount.get(severity) > 0) {
        return severity;
      }
    }
  };
  const queryParams = new Map<string, string>([
    ['tab', TabIndex.SecurityReport],
    ['digest', props.digest],
  ]);

  if (isLoading) {
    return <Skeleton width="50%"></Skeleton>;
  }

  if (isErrorString(error?.message)) {
    return <>Unable to get security details</>;
  }

  if (status === 'queued') {
    return <div>Queued</div>;
  } else if (status === 'failed') {
    return <div>Failed</div>;
  } else if (status === 'unsupported' || !hasFeatures) {
    return <div>Unsupported</div>;
  }

  if (vulnCount.size === 0) {
    return (
      <Link
        to={getTagDetailPath(
          location.pathname,
          props.org,
          props.repo,
          props.tag,
          queryParams,
        )}
        className={'pf-v5-u-display-inline-flex pf-v5-u-align-items-center'}
        style={{textDecoration: 'none'}}
      >
        <CheckCircleIcon
          color="green"
          style={{
            marginRight: '5px',
            marginBottom: '4px',
          }}
        />
        <span>None Detected</span>
      </Link>
    );
  }

  if (props.variant === Variant.condensed) {
    const highestSeverity: VulnerabilitySeverity = getHighestSeverity();
    return (
      <Link
        to={getTagDetailPath(
          location.pathname,
          props.org,
          props.repo,
          props.tag,
          queryParams,
        )}
        className={'pf-v5-u-display-inline-flex pf-v5-u-align-items-center'}
        style={{textDecoration: 'none'}}
      >
        <ExclamationTriangleIcon
          color={getSeverityColor(highestSeverity)}
          style={{
            marginRight: '5px',
            marginBottom: '4px',
          }}
        />
        <span>
          <b>{vulnCount.get(highestSeverity)}</b> {highestSeverity.toString()}
        </span>
      </Link>
    );
  }

  const counts = severityOrder
    .filter((severity) => vulnCount.has(severity))
    .map((severity) => {
      return (
        <div
          key={severity.toString()}
          className={'pf-v5-u-display-flex pf-v5-u-align-items-center'}
        >
          <ExclamationTriangleIcon
            color={getSeverityColor(severity)}
            style={{
              marginRight: '5px',
              marginBottom: '3px',
            }}
          />
          <span>
            <b>{vulnCount.get(severity)}</b> {severity.toString()}
          </span>
        </div>
      );
    });
  return (
    <Link
      to={getTagDetailPath(
        location.pathname,
        props.org,
        props.repo,
        props.tag,
        queryParams,
      )}
      style={{textDecoration: 'none'}}
    >
      {counts}
    </Link>
  );
}

export interface SecurityDetailsProps {
  org: string;
  repo: string;
  tag: string;
  digest: string;
  variant?: Variant | 'condensed' | 'full';
}
