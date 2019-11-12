/**
 * Adds an ng-if-media attribute that evaluates a media query and, if false, removes the element.
 */
angular.module('quay').directive('ngIfMedia', function ($animate, AngularHelper) {
  return {
    transclude: 'element',
    priority: 600,
    terminal: true,
    restrict: 'A',
    link: AngularHelper.buildConditionalLinker($animate, 'ngIfMedia', function(value) {
      return window.matchMedia(value).matches;
    })
  };
});

