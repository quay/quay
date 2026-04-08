import React from 'react';
import {useServiceStatus} from 'src/hooks/UseServiceStatus';
import {isNullOrUndefined} from 'src/libs/utils';
import './ServiceStatus.css';

export function ServiceStatus() {
  const {statusData} = useServiceStatus();

  if (isNullOrUndefined(statusData)) {
    return null;
  }

  return (
    <a
      href="https://status.redhat.com"
      className="service-status-icon"
      target="_blank"
      rel="noopener noreferrer"
    >
      <span className={`service-status-indicator ${statusData.indicator}`} />
      <span className="service-status-text">{statusData.description}</span>
    </a>
  );
}
