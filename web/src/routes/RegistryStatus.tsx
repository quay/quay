import {useServiceStatus} from 'src/hooks/UseServiceStatus';
import {formatDate, isNullOrUndefined} from 'src/libs/utils';
import './RegistryStatus.css';
import Conditional from 'src/components/empty/Conditional';
import {OutlinedCalendarAltIcon} from '@patternfly/react-icons';

export default function RegistryStatus() {
  const {statusData} = useServiceStatus();

  if (isNullOrUndefined(statusData)) {
    return <></>;
  }

  return (
    <Conditional
      if={
        statusData.indicator != 'loading' &&
        (statusData.scheduled_maintenances?.length > 0 ||
          statusData.incidents?.length > 0)
      }
    >
      <div id="registry-status" className="announcement inline">
        {statusData.incidents.map((incident) => {
          return (
            <div key={incident.name} className="quay-service-status-message">
              <Conditional if={statusData.indicator != 'loading'}>
                <span
                  className={`quay-service-status-indicator ${statusData.indicator}`}
                ></span>
                <a
                  href={incident.shortlink}
                  className="quay-service-status-description"
                >
                  {incident.name}
                </a>
              </Conditional>
            </div>
          );
        })}

        {statusData.scheduled_maintenances.map((scheduled) => {
          return (
            <div key={scheduled.name}>
              <span className="quay-service-status-message">
                <Conditional if={scheduled.status == 'scheduled'}>
                  <OutlinedCalendarAltIcon style={{marginRight: '6px'}} />{' '}
                  Scheduled for {formatDate(scheduled.scheduled_for)}:{' '}
                </Conditional>
                <Conditional
                  if={
                    scheduled.status == 'in_progress' ||
                    scheduled.status == 'verifying'
                  }
                >
                  <b style={{color: 'orange'}}>In progress: </b>
                </Conditional>
                <span>
                  <a
                    href={scheduled.shortlink}
                    className="quay-service-status-description"
                  >
                    {scheduled.name}
                  </a>
                </span>
              </span>
            </div>
          );
        })}
      </div>
    </Conditional>
  );
}
