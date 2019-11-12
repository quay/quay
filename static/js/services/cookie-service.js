/**
 * Helper service for working with cookies.
 */
angular.module('quay').factory('CookieService', ['$cookies', function($cookies) {
  var cookieService = {};
  cookieService.putPermanent = function(name, value) {
    document.cookie = escape(name) + "=" + escape(value) + "; expires=Fri, 31 Dec 9999 23:59:59 GMT; path=/";
  };

  cookieService.putSession = function(name, value) {
    $cookies.put(name, value);
  };

  cookieService.clear = function(name) {
    $cookies.remove(name);
  };

  cookieService.get = function(name) {
    return $cookies.get(name);
  };

  return cookieService;
}]);
