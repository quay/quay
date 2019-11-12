/**
 * Filter which converts an interval of time to a human-readable format.
 */
angular.module('quay').filter('humanizeInterval', function() {
  return function(seconds) {
    let minute = 60;
    let hour = minute * 60;
    let day = hour * 24;
    let week = day * 7;

    if (seconds % week == 0) return (seconds / week) + ' weeks';
    if (seconds % day == 0) return (seconds / day) + ' days';
    if (seconds % hour == 0) return (seconds / hour) + ' hours';
    if (seconds % minute == 0) return (seconds / minute) + ' minutes';
    return seconds + ' seconds';
  }
});