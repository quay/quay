/**
 * Service which provides access to the various keys defined in configuration, and working with
 * external services that rely on those keys.
 */
angular.module('quay').factory('KeyService', ['$location', 'Config', function($location, Config) {
  var keyService = {}
  var oauth = window.__oauth;

  keyService['stripePublishableKey'] = Config['STRIPE_PUBLISHABLE_KEY'];

  keyService['gitlabTriggerClientId'] = oauth['GITLAB_TRIGGER_CONFIG']['CLIENT_ID'];
  keyService['githubTriggerClientId'] = oauth['GITHUB_TRIGGER_CONFIG']['CLIENT_ID'];

  keyService['gitlabRedirectUri'] = Config.getUrl('/oauth2/gitlab/callback');
  keyService['githubRedirectUri'] = Config.getUrl('/oauth2/github/callback');
  keyService['googleRedirectUri'] = Config.getUrl('/oauth2/google/callback');

  keyService['githubTriggerEndpoint'] = oauth['GITHUB_TRIGGER_CONFIG']['GITHUB_ENDPOINT'];
  keyService['githubTriggerAuthorizeUrl'] = oauth['GITHUB_TRIGGER_CONFIG']['AUTHORIZE_ENDPOINT'];

  keyService['gitlabTriggerEndpoint'] = oauth['GITLAB_TRIGGER_CONFIG']['GITLAB_ENDPOINT'];
  keyService['gitlabTriggerAuthorizeUrl'] = oauth['GITLAB_TRIGGER_CONFIG']['AUTHORIZE_ENDPOINT'];

  keyService.getConfiguration = function(parent, key) {
    return oauth[parent][key];
  };

  keyService.isEnterprise = function(service) {
    switch (service) {
      case 'github':
        var loginUrl = oauth['GITHUB_LOGIN_CONFIG']['AUTHORIZE_ENDPOINT'];
        return loginUrl.indexOf('https://github.com/') < 0;

      case 'github-trigger':
        return keyService['githubTriggerAuthorizeUrl'].indexOf('https://github.com/') < 0;
    }

    return false;
  };

  return keyService;
}]);
