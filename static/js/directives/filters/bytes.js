/**
 * Filter which displays bytes with suffixes.
 */
angular.module('quay').filter('bytes', function() {
  return function(bytes, precision) {
    if (!bytes || isNaN(parseFloat(bytes)) || !isFinite(bytes)) return 'Unknown';
    if (typeof precision === 'undefined') precision = 1;
    var units = ['bytes', 'kB', 'MB', 'GB', 'TB', 'PB'],
    number = Math.floor(Math.log(bytes) / Math.log(1024));
    return (bytes / Math.pow(1024, Math.floor(number))).toFixed(precision) + ' ' + units[number];
  }
});