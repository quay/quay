/**
 * Element for managing the applications authorized by a user.
 */
angular.module('quay').directive('authorizedAppsManager', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/authorized-apps-manager.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'user': '=user',
      'isEnabled': '=isEnabled'
    },
    controller: function($scope, $element, ApiService) {
      $scope.$watch('isEnabled', function(enabled) {
        if (!enabled) { return; }
        loadAuthedApps();
      });

      var loadAuthedApps = function() {
        if ($scope.authorizedAppsResource) { return; }

        $scope.authorizedAppsResource = ApiService.listUserAuthorizationsAsResource().get(function(resp) {
          $scope.authorizedApps = resp['authorizations'];
        });
      };

      $scope.deleteAccess = function(accessTokenInfo) {
        var params = {
          'access_token_uuid': accessTokenInfo['uuid']
        };

        ApiService.deleteUserAuthorization(null, params).then(function(resp) {
          $scope.authorizedApps.splice($scope.authorizedApps.indexOf(accessTokenInfo), 1);
        }, ApiService.errorDisplay('Could not revoke authorization'));
      };
    }
  };
  return directiveDefinitionObject;
});