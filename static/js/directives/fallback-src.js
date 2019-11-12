/**
 * Adds a fallback-src attribute, which is used as the source for an <img> tag if the main
 * image fails to load.
 */
angular.module('quay').directive('fallbackSrc', function () {
  return {
    restrict: 'A',
    link: function postLink(scope, element, attributes) {
      element.bind('error', function() {
        angular.element(this).attr("src", attributes.fallbackSrc);
      });
    }
  };
});