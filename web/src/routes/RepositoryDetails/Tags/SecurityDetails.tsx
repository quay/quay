import {Skeleton} from '@patternfly/react-core';
import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
  EyeSlashIcon,
} from '@patternfly/react-icons';
import {useEffect, useState} from 'react';
import {Link, useLocation} from 'react-router-dom';
import {useRecoilState, useSetRecoilState} from 'recoil';
import {
  SecurityDetailsErrorState,
  SecurityDetailsState,
  securityDetailsCallStateSelector,
} from 'src/atoms/SecurityDetailsState';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {getSeverityColor} from 'src/libs/utils';
import {addDisplayError, isErrorString} from 'src/resources/ErrorHandling';
import {
  SecurityDetailsResponse,
  VulnerabilitySeverity,
  getSecurityDetails,
} from 'src/resources/TagResource';
import {getTagDetailPath} from 'src/routes/NavigationPath';
import {TabIndex} from 'src/routes/TagDetails/Types';

enum Variant {
  condensed = 'condensed',
  full = 'full',
}

export default function SecurityDetails(props: SecurityDetailsProps) {
  const config = useQuayConfig();
  const [status, setStatus] = useState<string>();
  const [hasFeatures, setHasFeatures] = useState<boolean>(false);
  const [vulnCount, setVulnCount] =
    useState<Map<VulnerabilitySeverity, number>>();
  const [loading, setLoading] = useState<boolean>(true);
  const [err, setErr] = useState<string>();
  const setGlobalErr = useSetRecoilState(SecurityDetailsErrorState);
  const setGlobalData = useSetRecoilState(SecurityDetailsState);
  const [reloadGlobalData, setReloadGlobalData] = useRecoilState(
    securityDetailsCallStateSelector(props.digest),
  );
  const location = useLocation();

  const severityOrder = [
    VulnerabilitySeverity.Critical,
    VulnerabilitySeverity.High,
    VulnerabilitySeverity.Medium,
    VulnerabilitySeverity.Low,
    VulnerabilitySeverity.Negligible,
    VulnerabilitySeverity.Unknown,
    VulnerabilitySeverity.Suppressed,
  ];

  const getHighestSeverity = () => {
    for (const severity of severityOrder) {
      if (vulnCount.get(severity) != null && vulnCount.get(severity) > 0) {
        return severity;
      }
    }
  };

  const loadSecurityDetails = async () => {
    try {
      setLoading(true);
      setGlobalData(undefined);

      const securityDetails: SecurityDetailsResponse = await getSecurityDetails(
        props.org,
        props.repo,
        props.digest,
      );

      const vulns = new Map<VulnerabilitySeverity, number>();
      if (securityDetails.data) {
        if (props.cacheResults) setGlobalData(securityDetails);
        setHasFeatures(securityDetails.data.Layer.Features.length > 0);
        for (const feature of securityDetails.data.Layer.Features) {
          if (feature.Vulnerabilities) {
            for (const vuln of feature.Vulnerabilities) {
              if (vuln.Severity in VulnerabilitySeverity) {
                if (
                  config?.features.SECURITY_VULNERABILITY_SUPPRESSION &&
                  vuln.SuppressedBy
                ) {
                  vulns.set(
                    VulnerabilitySeverity.Suppressed,
                    (vulns.get(VulnerabilitySeverity.Suppressed) || 0) + 1,
                  );
                  continue;
                }

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
      const message = addDisplayError('Unable to get security details', error);
      if (props.cacheResults) setGlobalErr(message);
      setErr(message);
      setLoading(false);
    }
  };

  // load the security details on initial load of the component
  useEffect(() => {
    if (props.digest !== '') {
      (async () => {
        await loadSecurityDetails();
        setReloadGlobalData(false);
      })();
    }
  }, [props.digest]);

  // reload the security details when other components change vulnerability reporting
  useEffect(() => {
    if (props.digest !== '' && reloadGlobalData) {
      (async () => {
        await loadSecurityDetails();
        setReloadGlobalData(false);
      })();
    }
  }, [reloadGlobalData]);

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
          {severity === 'Suppressed' ? (
            <EyeSlashIcon
              style={{
                color: 'var(--pf-global--disabled-color--200)',
                marginRight: '5px',
                marginBottom: '3px',
              }}
            />
          ) : (
            <ExclamationTriangleIcon
              color={getSeverityColor(severity)}
              style={{
                marginRight: '5px',
                marginBottom: '3px',
              }}
            />
          )}
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
