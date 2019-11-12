/**
 * Feature flags.
 */
angular.module('quay-config').factory('Features', [function() {
  if (!window.__features) {
    return {};
  }

  var features = window.__features;
  features.getFeature = function(name, opt_defaultValue) {
    var value = features[name];
    if (value == null) {
      return opt_defaultValue;
    }
    return value;
  };

  features.hasFeature = function(name) {
    return !!features.getFeature(name);
  };

  features.matchesFeatures = function(list) {
    for (var i = 0; i < list.length; ++i) {
      var value = features.getFeature(list[i]);
      if (!value) {
        return false;
      }
    }
    return true;
  };

  return features;
}]);

/**
 * Application configuration.
 */
angular.module('quay-config').factory('Config', ['Features', function(Features) {
  if (!window.__config) {
    return {};
  }

  var config = window.__config;
  config.getDomain = function() {
    return config['SERVER_HOSTNAME'];
  };

  config.getHost = function(opt_auth) {
    var auth = opt_auth;
    if (auth) {
      auth = auth + '@';
    }

    return config['PREFERRED_URL_SCHEME'] + '://' + auth + config['SERVER_HOSTNAME'];
  };

  config.getHttp = function() {
    return config['PREFERRED_URL_SCHEME'];
  };

  config.getUrl = function(opt_path) {
    var path = opt_path || '';
    return config['PREFERRED_URL_SCHEME'] + '://' + config['SERVER_HOSTNAME'] + path;
  };

  config.getValue = function(name, opt_defaultValue) {
    var value = config[name];
    if (value == null) {
      return opt_defaultValue;
    }
    return value;
  };

  config.getEnterpriseLogo = function(opt_defaultValue) {
    if (!config.ENTERPRISE_LOGO_URL) {
      if (opt_defaultValue) {
        return opt_defaultValue;
      }

      if (Features.BILLING) {
        return '/static/img/quay-horizontal-color.svg';
      } else {
        return '/static/img/QuayEnterprise_horizontal_color.svg';
      }
    }

    return config.ENTERPRISE_LOGO_URL;
  };

  return config;
}]);