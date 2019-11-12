/**
 * Reversing filter.
 */
angular.module('quay').filter('reverse', function() {
  return function(items) {
    return items.slice().reverse();
  };
});