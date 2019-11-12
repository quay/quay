/**
 * Adds an ng-name attribute which sets the name of a form field. Using the normal name field
 * in Angular 1.3 works, but we're still on 1.2.
 */
angular.module('quay').directive('ngName', function () {
  return function (scope, element, attr) {
    scope.$watch(attr.ngName, function (name) {
      element.attr('name', name);
    });
  };
});