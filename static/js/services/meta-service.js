/**
 * Service which helps set the contents of the <meta> tags (and the <title> of a page).
 */
angular.module('quay').factory('MetaService', ['$interpolate', '$timeout', function($interpolate, $timeout) {
  var metaService = {};

  var interpolate = function(page, expr) {
    if (!expr) {
      return null;
    }

    var inter = $interpolate(expr, true, null, true);
    if (!inter) {
      return expr.toString();
    }

    return inter(page.scope);
  };

  var interpolationPromise = function(page, fieldGetter) {    
    return new Promise(function(resolve, reject) {
      if (!page || !page.$$route) {
        resolve(null);
        return;
      }

      if (page.scope) {
        resolve(interpolate(page, fieldGetter()));
        return;
      }

      // Timeout needed because page.scope is initially undefined.
      $timeout(function() {
        resolve(interpolationPromise(page, fieldGetter));
      }, 10);
    });
  };

  metaService.getTitle = function(page) {
    return interpolationPromise(page, () =>  page.$$route.title);
  };

  metaService.getDescription = function(page) {
    return interpolationPromise(page, () =>  page.$$route.description);
  };

  return metaService;
}]);
