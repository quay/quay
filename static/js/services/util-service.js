var urlParseURL = require('url-parse');

var UrlBuilder = function(initial_url) {  
  this.url = urlParseURL(initial_url || '', '/');
};

UrlBuilder.prototype.setQueryParameter = function(paramName, paramValue) {
  if (paramValue == null) {
    return;
  }

  this.url.query = this.url.query || {};
  this.url.query[paramName] = paramValue;
};

UrlBuilder.prototype.toString = function() {
  return this.url.toString();
};


/**
 * Service which exposes various utility methods.
 */
angular.module('quay').factory('UtilService', ['$sanitize', 'markdownConverter',
  function($sanitize, markdownConverter) {
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

    utilService.getMarkedDown = function(string) {
      return markdownConverter.makeHtml(string || '');
    };

    utilService.getFirstMarkdownLineAsText = function(commentString, placeholderNeeded) {
      if (!commentString) {
        if (placeholderNeeded) {
          return '<p style="visibility:hidden">placeholder</p>';
        }
        return '';
      }

      var lines = commentString.split('\n');
      var MARKDOWN_CHARS = {
        '#': true,
        '-': true,
        '>': true,
        '`': true
      };

      for (var i = 0; i < lines.length; ++i) {
        // Skip code lines.
        if (lines[i].indexOf('    ') == 0) {
          continue;
        }

        // Skip empty lines.
        if ($.trim(lines[i]).length == 0) {
          continue;
        }

        // Skip control lines.
        if (MARKDOWN_CHARS[$.trim(lines[i])[0]]) {
          continue;
        }

        return utilService.getMarkedDown(lines[i]);
      }

      return '';
    };

    utilService.getFirstMarkdownLineAsString = function(commentString) {
      return utilService.getFirstMarkdownLineAsText(commentString, false).replace('</p>', '')
                                                                         .replace('<p>', '');
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
      var path = '';

      for (var i = 0; i < arguments.length; ++i) {
        if (i > 0) {
          path += '/';
        }
        path += encodeURI(arguments[i])
      }
    
      return new UrlBuilder(path);
    };

    utilService.textToSafeHtml = function(text) {
      return $sanitize(utilService.escapeHtmlString(text));
    };

    utilService.UrlBuilder = UrlBuilder;

    utilService.removeHtmlTags = function(text){
      try {
        return new DOMParser().parseFromString(text, 'text/html').body.textContent || text;
      } catch(e) {
        return text;
      }

    };

    return utilService;
}]);
