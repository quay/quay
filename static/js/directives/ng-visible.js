/**
 * Adds an ng-visible attribute that hides an element if the expression evaluates to false.
 */
angular.module('quay').directive('ngVisible', function () {
  return function (scope, element, attr) {
    scope.$watch(attr.ngVisible, function (visible) {
      element.css('visibility', visible ? 'visible' : 'hidden');
    });
  };
});