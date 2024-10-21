import {Link, useLocation} from 'react-router-dom';
import {Skeleton} from '@patternfly/react-core';
import {getTagDetailPath} from 'src/routes/NavigationPath';
import {TabIndex} from 'src/routes/TagDetails/Types';
import {
  ExclamationTriangleIcon,
  CheckCircleIcon,
} from '@patternfly/react-icons';
import {getSeverityColor} from 'src/libs/utils';
import {VulnerabilitySeverity} from 'src/resources/ManifestSecurityResource';
import {useManifestSecurity} from 'src/hooks/UseManifestSecurity';

enum Variant {
  condensed = 'condensed',
  full = 'full',
}

export interface SecurityDetailsProps {
  org: string;
  repo: string;
  tag: string;
  digest: string;
  variant?: Variant | 'condensed' | 'full';
  load?: boolean;
}

SecurityDetails.defaultProps = {
  load: true,
};

export default function SecurityDetails(props: SecurityDetailsProps) {
  const location = useLocation();

  const severityOrder = [
    VulnerabilitySeverity.Critical,
    VulnerabilitySeverity.High,
    VulnerabilitySeverity.Medium,
    VulnerabilitySeverity.Low,
    VulnerabilitySeverity.Negligible,
    VulnerabilitySeverity.Unknown,
  ];

  const {securityDetails, isSecurityDetailsLoading, isSecurityDetailsError} =
    useManifestSecurity(
      props.org,
      props.repo,
      props.digest,
      props.load && props.digest !== '',
    );

  const queryParams = new Map<string, string>([
    ['tab', TabIndex.SecurityReport],
    ['digest', props.digest],
  ]);

  if (isSecurityDetailsLoading) {
    return <Skeleton width="50%"></Skeleton>;
  }

  if (isSecurityDetailsError) {
    return <>Unable to get security details</>;
  }

  if (securityDetails === null || securityDetails === undefined) {
    return <>Security details not available</>;
  }

  if (securityDetails.status === 'queued') {
    return <div>Queued</div>;
  } else if (securityDetails.status === 'failed') {
    return <div>Failed</div>;
  } else if (
    securityDetails.status === 'unsupported' ||
    securityDetails.data.Layer.Features.length == 0
  ) {
    return <div>Unsupported</div>;
  }

  const vulns = new Map<VulnerabilitySeverity, number>();

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

  if (vulns.size === 0) {
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
    let highestSeverity: VulnerabilitySeverity;

    for (const severity of severityOrder) {
      if (vulns.get(severity) != null && vulns.get(severity) > 0) {
        highestSeverity = severity;
        break;
      }
    }

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
          <b>{vulns.get(highestSeverity)}</b> {highestSeverity.toString()}
        </span>
      </Link>
    );
  }

  const counts = severityOrder
    .filter((severity) => vulns.has(severity))
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
            <b>{vulns.get(severity)}</b> {severity.toString()}
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
