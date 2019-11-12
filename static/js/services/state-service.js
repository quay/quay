/**
 * Service which monitors the current state of the registry.
 */
angular.module('quay')
       .factory('StateService', ['$rootScope', '$timeout', function($rootScope, $timeout) {
  var stateService = {};

  var currentState = {
    'inReadOnlyMode': false
  };

  stateService.inReadOnlyMode = function() {
    return currentState.inReadOnlyMode;
  };

  stateService.setInReadOnlyMode = function() {
    currentState.inReadOnlyMode = true;
  };

  stateService.updateStateIn = function(scope, opt_callback) {
    scope.$watch(function () { return stateService.currentState(); }, function (currentState) {
      $timeout(function(){
        scope.currentRegistryState = currentState;
        if (opt_callback) {
          opt_callback(currentState);
        }
      }, 0, false);
    }, true);
  };

  stateService.currentState = function() {
    return currentState;
  };

  // Update the state in the root scope.
  stateService.updateStateIn($rootScope);

  return stateService;
}]);
