import {useEffect, useState} from 'react';
import {
  SecurityDetailsResponse,
  getSecurityDetails,
} from 'src/resources/TagResource';
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
import {
  SecurityDetailsErrorState,
  SecurityDetailsState,
} from 'src/atoms/SecurityDetailsState';
import {useResetRecoilState, useSetRecoilState} from 'recoil';
import {addDisplayError, isErrorString} from 'src/resources/ErrorHandling';

enum Variant {
  condensed = 'condensed',
  full = 'full',
}

export default function SecurityDetails(props: SecurityDetailsProps) {
  const [status, setStatus] = useState<string>();
  const [hasFeatures, setHasFeatures] = useState<boolean>(false);
  const [vulnCount, setVulnCount] =
    useState<Map<VulnerabilitySeverity, number>>();
  const [loading, setLoading] = useState<boolean>(true);
  const [err, setErr] = useState<string>();
  const setGlobalErr = useSetRecoilState(SecurityDetailsErrorState);
  const setGlobalData = useSetRecoilState(SecurityDetailsState);
  const location = useLocation();

  const severityOrder = [
    VulnerabilitySeverity.Critical,
    VulnerabilitySeverity.High,
    VulnerabilitySeverity.Medium,
    VulnerabilitySeverity.Low,
    VulnerabilitySeverity.Negligible,
    VulnerabilitySeverity.Unknown,
  ];

  const getHighestSeverity = () => {
    for (const severity of severityOrder) {
      if (vulnCount.get(severity) != null && vulnCount.get(severity) > 0) {
        return severity;
      }
    }
  };

  useEffect(() => {
    if (props.digest !== '') {
      (async () => {
        try {
          setLoading(true);
          const securityDetails: SecurityDetailsResponse =
            await getSecurityDetails(props.org, props.repo, props.digest);
          const vulns = new Map<VulnerabilitySeverity, number>();
          if (securityDetails.data) {
            if (props.cacheResults) setGlobalData(securityDetails);
            setHasFeatures(securityDetails.data.Layer.Features.length > 0);
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
          setStatus(securityDetails.status);
          setVulnCount(vulns);
          setLoading(false);
        } catch (error: any) {
          console.error(error);
          const message = addDisplayError(
            'Unable to get security details',
            error,
          );
          if (props.cacheResults) setGlobalErr(message);
          setErr(message);
          setLoading(false);
        }
      })();
    }
  }, [props.digest]);
  const queryParams = new Map<string, string>([
    ['tab', TabIndex.SecurityReport],
    ['digest', props.digest],
  ]);

  if (loading) {
    return <Skeleton width="50%"></Skeleton>;
  }

  if (isErrorString(err)) {
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
  cacheResults?: boolean;
}
