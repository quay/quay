import {useEffect, useState} from 'react';
import {isNullOrUndefined} from 'src/libs/utils';

const STATUSPAGE_PAGE_ID = 'dn6mqn7xvzz3';
const STATUSPAGE_QUAY_ID = 'cllr1k2dzsf7';
const statusToIndicator = {
  operational: {
    indicator: 'none',
    description: 'All Systems Operational',
  },
  degraded_performance: {
    indicator: 'minor',
    description: 'Degraded Performance',
  },
  partial_outage: {
    indicator: 'major',
    description: 'Partial System Outage',
  },
  major_outage: {
    indicator: 'critical',
    description: 'Major Service Outage',
  },
};

interface StatusData {
  indicator: string;
  description: string;
  incidents: any[];
  components: any[];
  degraded_components: any[];
  scheduled_maintenances: any[];
}

export function useServiceStatus() {
  const [statusData, setStatusData] = useState<StatusData>(null);
  if (isNullOrUndefined(StatusPage)) {
    return {};
  }
  useEffect(() => {
    const statusPageHandler = new StatusPage.page({page: STATUSPAGE_PAGE_ID});
    statusPageHandler.summary({
      success: (data) => {
        if (!data) {
          return;
        }

        const quayData: StatusData = {
          indicator: '',
          description: '',
          incidents: [],
          components: [],
          scheduled_maintenances: [],
          degraded_components: [],
        };
        const quayComponent = data.components.find(
          (component) => component.id === STATUSPAGE_QUAY_ID,
        );
        if (!quayComponent) {
          return;
        }
        const subComponentIds = quayComponent.components || [];

        // incidents
        const incidents = data.incidents.filter((incident) => {
          return incident.components.some((component) =>
            subComponentIds.includes(component.id),
          );
        });
        quayData.incidents = incidents;

        // components
        const subComponents = data.components.filter((component) =>
          subComponentIds.includes(component.id),
        );
        quayData.components = subComponents;
        quayData.degraded_components = subComponents.filter(
          (component) => component.status !== 'operational',
        );

        // scheduled_maintenances
        const scheduledMaintenances = data.scheduled_maintenances.filter(
          (scheduledMaintenance) => {
            return scheduledMaintenance.components.some((component) =>
              subComponentIds.includes(component.id),
            );
          },
        );
        quayData.scheduled_maintenances = scheduledMaintenances;

        // status.indicator
        quayData.indicator = statusToIndicator[quayComponent.status].indicator;

        // status.description
        quayData.description =
          statusToIndicator[quayComponent.status].description;

        setStatusData(quayData);
      },
    });
  }, []);

  return {
    statusData,
  };
}
