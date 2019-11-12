/**
 * Element for managing the applications of an organization.
 */
angular.module('quay').directive('applicationManager', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/application-manager.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'organization': '=organization',
      'makevisible': '=makevisible'
    },
    controller: function($scope, $element, ApiService) {
      $scope.loading = false;
      $scope.applications = [];
      $scope.feedback = null;

      $scope.createApplication = function(appName) {
        if (!appName) { return; }

        var params = {
          'orgname': $scope.organization.name
        };

        var data = {
          'name': appName
        };

        ApiService.createOrganizationApplication(data, params).then(function(resp) {
          $scope.applications.push(resp);

          $scope.feedback = {
            'kind': 'success',
            'message': 'Application {application_name} created',
            'data': {
              'application_name': appName
            }
          };

        }, ApiService.errorDisplay('Cannot create application'));
      };

      var update = function() {
        if (!$scope.organization || !$scope.makevisible) { return; }
        if ($scope.loading) { return; }

        $scope.loading = true;

        var params = {
          'orgname': $scope.organization.name
        };

        ApiService.getOrganizationApplications(null, params).then(function(resp) {
          $scope.loading = false;
          $scope.applications = resp['applications'] || [];
        });
      };

      $scope.$watch('organization', update);
      $scope.$watch('makevisible', update);
    }
  };
  return directiveDefinitionObject;
});