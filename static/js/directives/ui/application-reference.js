/**
 * An element which shows information about an OAuth application and provides a clickable link
 * for displaying a dialog with further information. Unlike application-info, this element is
 * intended for the *owner* of the application (since it requires the client ID).
 */
angular.module('quay').directive('applicationReference', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/application-reference.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'title': '=title',
      'clientId': '=clientId'
    },
    controller: function($scope, $element, ApiService, $modal) {
      $scope.showAppDetails = function() {
        var params = {
          'client_id': $scope.clientId
        };

        ApiService.getApplicationInformation(null, params).then(function(resp) {
          $scope.applicationInfo = resp;
          $modal({
            title: 'Application Information',
            scope: $scope,
            template: '/static/directives/application-reference-dialog.html',
            show: true
          });
        }, ApiService.errorDisplay('Application could not be found'));
      };
    }
  };
  return directiveDefinitionObject;
});
