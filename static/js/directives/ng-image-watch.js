/**
 * Adds a ng-image-watch attribute, which is a callback invoked when the image is loaded or fails.
 */
angular.module('quay').directive('ngImageWatch', function ($parse) {
  return {
    restrict: 'A',
    compile: function($element, attr) {
      var fn = $parse(attr['ngImageWatch']);
      return function(scope, element) {
        element.bind('error', function() {
          scope.$apply(function() {
            fn(scope, {result: false});
          })
        });

        element.bind('load', function() {
          scope.$apply(function() {
            fn(scope, {result: true});
          })
        });
      }
    }
  };
});