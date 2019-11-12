/**
 * Adds both target="_blank" and rel="noopener" to the marked anchor tag.
 * Background on noopener: https://mathiasbynens.github.io/rel-noopener/
 */
angular.module('quay').directive('ngSafenewtab', function () {
  return function (scope, element, attr) {
    element.attr('target', '_blank');
    element.attr('rel', 'noopener noreferrer');
  };
});