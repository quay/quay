/**
 * Slice filter.
 */
angular.module('quay').filter('slice', function() {
  return function(arr, start, end) {
    return (arr || []).slice(start, end);
  };
});