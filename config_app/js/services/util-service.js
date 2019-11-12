/**
 * Service which exposes various utility methods.
 */
angular.module('quay-config').factory('UtilService', ['$sanitize',
    function($sanitize) {
      var utilService = {};

      var adBlockEnabled = null;

      utilService.isAdBlockEnabled = function(callback) {
        if (adBlockEnabled !== null) {
          callback(adBlockEnabled);
          return;
        }

        if(typeof blockAdBlock === 'undefined') {
          callback(true);
          return;
        }

        var bab = new BlockAdBlock({
          checkOnLoad: false,
          resetOnEnd: true
        });

        bab.onDetected(function() { adBlockEnabled = true; callback(true); });
        bab.onNotDetected(function() { adBlockEnabled = false; callback(false); });
        bab.check();
      };

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

      utilService.textToSafeHtml = function(text) {
        return $sanitize(utilService.escapeHtmlString(text));
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
