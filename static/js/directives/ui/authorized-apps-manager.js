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
    controller: function($scope, $element, ApiService, Config) {
      $scope.$watch('isEnabled', function(enabled) {
        if (!enabled) { return; }
        loadAuthedApps();
        loadAssignedAuthApps();
      });

      var loadAuthedApps = function() {
        if ($scope.authorizedAppsResource) { return; }

        $scope.authorizedAppsResource = ApiService.listUserAuthorizationsAsResource().get(function(resp) {
          $scope.authorizedApps = resp['authorizations'];
        });
      };

      var loadAssignedAuthApps = function(){
        if ($scope.assignedAuthAppsResource || !Config.FEATURE_ASSIGN_OAUTH_TOKEN) {
          $scope.assignedAuthApps = [];
          return;
        }

        $scope.assignedAuthAppsResource = ApiService.listAssignedAuthorizationsAsResource().get(function(resp) {
          $scope.assignedAuthApps = resp['authorizations'];
        });
      }

      $scope.deleteAccess = function(accessTokenInfo) {
        var params = {
          'access_token_uuid': accessTokenInfo['uuid']
        };

        ApiService.deleteUserAuthorization(null, params).then(function(resp) {
          $scope.authorizedApps.splice($scope.authorizedApps.indexOf(accessTokenInfo), 1);
        }, ApiService.errorDisplay('Could not revoke authorization'));
      };

      $scope.deleteAssignedAuthorization = function(assignedAuthorization){
        if(!Config.FEATURE_ASSIGN_OAUTH_TOKEN){
          return;
        }
        var params = {
          'assigned_authorization_uuid': assignedAuthorization['uuid']
        };

        ApiService.deleteAssignedAuthorization(null, params).then(function(resp) {
          $scope.assignedAuthApps.splice($scope.assignedAuthApps.indexOf(assignedAuthorization), 1);
        }, ApiService.errorDisplay('Could not revoke assigned authorization'));
      }

      $scope.getAuthorizationUrl = function(assignedAuthorization){
        let scopes = assignedAuthorization.scopes.map((scope) => scope.scope).join(' ');
        let url = "/oauth/authorize?";
        url += "response_type=" + assignedAuthorization.responseType;
        url += "&client_id=" + assignedAuthorization.application.clientId;
        url += "&scope=" + scopes;
        url += "&redirect_uri=" + assignedAuthorization.redirectUri;
        url += "&assignment_uuid=" + assignedAuthorization.uuid;
        return Config.getUrl(url);
      }
    }
  };
  return directiveDefinitionObject;
});
