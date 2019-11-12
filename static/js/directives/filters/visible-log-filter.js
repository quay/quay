/**
 * Filter for hiding logs that don't meet the allowed predicate.
 */
angular.module('quay').filter('visibleLogFilter', function () {
  return function (logs, allowed) {
    if (!allowed) {
      return logs;
    }

    var filtered = [];
    angular.forEach(logs, function (log) {
      if (allowed[log.kind]) {
        filtered.push(log);
      }
    });

    return filtered;
  };
});
