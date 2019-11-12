/**
 * Service which provides the OAuth scopes defined.
 */
angular.module('quay').factory('OAuthService', ['$location', 'Config', function($location, Config) {
  var oauthService = {};
  oauthService.SCOPES = window.__auth_scopes;
  return oauthService;
}]);