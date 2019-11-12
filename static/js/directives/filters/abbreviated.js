/**
 * Filter which displays numbers with suffixes.
 *
 * Based on: https://gist.github.com/pedrorocha-net/9aa21d5f34d9cc15d18f
 */
angular.module('quay').filter('abbreviated', function() {
  return function(number) {
    if (number >= 10000000) {
      return (number / 1000000).toFixed(0) + 'M'
    }

    if (number >= 1000000) {
      return (number / 1000000).toFixed(1) + 'M'
    }

    if (number >= 10000) {
      return (number / 1000).toFixed(0) + 'K'
    }

    if (number >= 1000) {
      return (number / 1000).toFixed(1) + 'K'
    }

    return number
  }
});
