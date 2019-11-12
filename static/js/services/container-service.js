/**
 * Helper service for working with the registry's container. Only works in enterprise.
 */
angular.module('quay').factory('ContainerService', ['ApiService', '$timeout', 'Restangular',

function(ApiService, $timeout, Restangular) {
  var containerService = {};
  containerService.restartContainer = function(callback) {
    ApiService.scShutdownContainer(null, null).then(function(resp) {
      $timeout(callback, 2000);
    }, ApiService.errorDisplay('Cannot restart container. Please report this to support.'))
  };

  containerService.scheduleStatusCheck = function(callback, opt_config) {
    $timeout(function() {
      containerService.checkStatus(callback, opt_config);
    }, 2000);
  };

  containerService.checkStatus = function(callback, opt_config) {
    var errorHandler = function(resp) {
      if (resp.status == 404 || resp.status == 502 || resp.status == -1) {
        // Container has not yet come back up, so we schedule another check.
        containerService.scheduleStatusCheck(callback, opt_config);
        return;
      }

      return ApiService.errorDisplay('Cannot load status. Please report this to support')(resp);
    };

    // If config is specified, override the API base URL from this point onward.
    if (opt_config && opt_config['SERVER_HOSTNAME']) {
      var scheme = opt_config['PREFERRED_URL_SCHEME'] || 'http';
      var baseUrl = scheme + '://' + opt_config['SERVER_HOSTNAME'] + '/api/v1/';
      Restangular.setBaseUrl(baseUrl);
    }

    ApiService.scRegistryStatus(null, null, /* background */true)
              .then(callback, errorHandler);
  };

  return containerService;
}]);
