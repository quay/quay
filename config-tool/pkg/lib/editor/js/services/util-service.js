/**
 * Service which exposes various utility methods.
 */
angular.module('quay-config').factory('UtilService', [
    function() {
      var utilService = {};

      utilService.isEmailAddress = function(val) {
        var emailRegex = /^[a-zA-Z0-9.!#$%&’*+/=?^_`{|}~-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*$/;
        return emailRegex.test(val);
      };

      utilService.escapeHtmlString = function(text) {
        var textStr = (text || '').toString();
        var adjusted = textStr.replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;")
          .replace(/"/g, "&quot;")
          .replace(/'/g, "&#039;");

        return adjusted;
      };

      utilService.stringToHTML = function(text) {
        text = utilService.escapeHtmlString(text);
        text = text.replace(/\n/g, '<br>');
        return text;
      };

      utilService.getRestUrl = function(args) {
        var url = '';
        for (var i = 0; i < arguments.length; ++i) {
          if (i > 0) {
            url += '/';
          }
          url += encodeURI(arguments[i])
        }
        return url;
      };

      return utilService;
    }])
  .factory('CoreDialog', [() => {
    var service = {};
    service['fatal'] = function(title, message) {
      bootbox.dialog({
        "title": title,
        "message": "<div class='alert-icon-container-container'><div class='alert-icon-container'><div class='alert-icon'></div></div></div>" + message,
        "buttons": {},
        "className": "co-dialog fatal-error",
        "closeButton": false
      });
    };

    return service;
  }]);
