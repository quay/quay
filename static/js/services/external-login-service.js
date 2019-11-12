/**
 * Service which exposes the supported external logins.
 */
angular.module('quay').factory('ExternalLoginService', ['Features', 'Config', 'ApiService',
  function(Features, Config, ApiService) {
  var externalLoginService = {};

  externalLoginService.EXTERNAL_LOGINS = window.__external_login || [];

  externalLoginService.getLoginUrl = function(loginService, action, callback) {
    var errorDisplay = ApiService.errorDisplay('Could not load external login service ' +
                                               'information. Please contact your service ' +
                                               'administrator.')

    var params = {
      'service_id': loginService['id']
    };

    var data = {
      'kind': action
    };

    ApiService.retrieveExternalLoginAuthorizationUrl(data, params).then(function(resp) {
      callback(resp['auth_url']);
    }, errorDisplay);
  };

  externalLoginService.hasSingleSignin = function() {
    return externalLoginService.EXTERNAL_LOGINS.length == 1 && !Features.DIRECT_LOGIN;
  };

  externalLoginService.getSingleSigninUrl = function(callback) {
    if (!externalLoginService.hasSingleSignin()) {
      return callback(null);
    }

    // If there is a single external login service and direct login is disabled,
    // then redirect to the external login directly.
    externalLoginService.getLoginUrl(externalLoginService.EXTERNAL_LOGINS[0], 'login', callback);
  };

  return externalLoginService;
}]);