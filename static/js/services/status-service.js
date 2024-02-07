/**
 * Helper service for retrieving the statuspage status of the quay service.
 */
angular.module('quay').factory('StatusService', ['Features', function(Features) {
  if (!Features.BILLING) {
    return {
      getStatus: function(callback) {}
    };
  }

  var STATUSPAGE_PAGE_ID = 'dn6mqn7xvzz3';
  var STATUSPAGE_QUAY_ID = 'cllr1k2dzsf7';
  var STATUSPAGE_SRC = 'https://cdn.statuspage.io/se-v2.js';
  var statusToIndicator = {
    operational: {
      indicator: 'none',
      description: 'All Systems Operational'
    },
    degraded_performance: {
      indicator: 'minor',
      description: 'Degraded Performance'
    },
    partial_outage: {
      indicator: 'major',
      description: 'Partial System Outage'
    },
    major_outage: {
      indicator: 'critical',
      description: 'Major Service Outage'
    },
  }
  var statusPageHandler = null;
  var statusPageData = null;
  var callbacks = [];

  var handleGotData = function(data) {
    if (!data) { return; }
    statusPageData = data;

    const quayData = {status:{}};
    const quayComponent = data.components.find((component) => component.id === STATUSPAGE_QUAY_ID);
    if(!quayComponent) {return;}
    const subComponentIds = quayComponent.components || [];

    // incidents
    const incidents = data.incidents.filter((incident) => {
      return incident.components.some((component) => subComponentIds.includes(component.id));
    });
    quayData.incidents = incidents;

    // components
    const subComponents = data.components.filter((component) => subComponentIds.includes(component.id));
    quayData.components = subComponents;

    // scheduled_maintenances
    const scheduledMaintenances = data.scheduled_maintenances.filter((scheduledMaintenance) => {
      return scheduledMaintenance.components.some((component) => subComponentIds.includes(component.id));
    });
    quayData.scheduled_maintenances = scheduledMaintenances;

    // status.indicator
    quayData.status.indicator = statusToIndicator[quayComponent.status].indicator;

    // status.description
    quayData.status.description = statusToIndicator[quayComponent.status].description;

    for (var i = 0; i < callbacks.length; ++i) {
      callbacks[i](quayData);
    }

    callbacks = [];
  };

  $.getScript(STATUSPAGE_SRC, function(){
    statusPageHandler = new StatusPage.page({ page: STATUSPAGE_PAGE_ID });
    statusPageHandler.summary({
      success : handleGotData
    });
  });

  var statusService = {};
  statusService.getStatus = function(callback) {
    callbacks.push(callback);
    handleGotData(statusPageData);
  };

  return statusService;
}]);
