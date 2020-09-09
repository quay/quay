/**
 * Service which exposes the server-defined API as a nice set of helper methods and automatic
 * callbacks.
 */
angular.module("quay-config").factory("ApiService", [
  "Restangular",
  "$q",
  "UtilService",
  function (Restangular, $q, UtilService) {
    var apiService = {};

    apiService.getConfig = function () {
      return Restangular.one("config").get();
    };

    apiService.validateConfig = function (config) {
      return Restangular.one("config/validate").post(null, config);
    };

    apiService.commitToOperator = function (config) {
      return Restangular.one("config/commitToOperator").post(null, config);
    };

    apiService.downloadConfig = function (config) {
      return Restangular.one("config/downloadConfig").post(null, config);
    };

    apiService.getCertificates = function () {
      return Restangular.one("certificates").get();
    };

    apiService.getErrorMessage = function (resp, defaultMessage) {
      var message = defaultMessage;
      if (resp && resp["data"]) {
        //TODO: remove error_message and error_description (old style error)
        message =
          resp["data"]["detail"] ||
          resp["data"]["error_message"] ||
          resp["data"]["message"] ||
          resp["data"]["error_description"] ||
          message;
      }

      return message;
    };

    apiService.errorDisplay = function (defaultMessage, opt_handler) {
      return function (resp) {
        var message = apiService.getErrorMessage(resp, defaultMessage);
        if (opt_handler) {
          var handlerMessage = opt_handler(resp);
          if (handlerMessage) {
            message = handlerMessage;
          }
        }

        message = UtilService.stringToHTML(message);
        alert(message);
      };
    };

    return apiService;
  },
]);
