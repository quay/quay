import moment from "moment"

function isNumber(arg) {
  return typeof arg === 'number';
}

/**
 * Filter which displays a date in a human-readable format.
 */
angular.module('quay').filter('humanizeDate', function() {
  return function(input) {
    if (isNumber(input)) {
      return moment.unix(input).format('lll'); // Unix Timestamp
    } else {
      return moment(input).format('lll');
    }
  }
});
