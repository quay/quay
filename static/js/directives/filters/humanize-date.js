import { isNumber } from "util"
import moment from "moment"

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