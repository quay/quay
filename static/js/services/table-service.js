/**
 * Service which provides helper methods for constructing and managing tabular data.
 */
angular.module('quay').factory('TableService', ['ViewArray', function(ViewArray) {
  var tableService = {};

  tableService.tablePredicateClass = function(name, predicate, reverse) {
    if (name != predicate) {
      return '';
    }

    return 'current ' + (reverse ? 'reversed' : '');
  };

  tableService.orderBy = function(predicate, options) {
    if (predicate == options.predicate) {
      options.reverse = !options.reverse;
      return;
    }

    options.reverse = false;
    options.predicate = predicate;
  };

  tableService.getReversedTimestamp = function(datetime) {
    if (!datetime) {
      return -Number.MAX_VALUE;
    }

    return (new Date(datetime)).valueOf();
  };

  tableService.buildOrderedItems = function(items, options, filterFields, numericFields, opt_extrafilter) {
    var orderedItems = ViewArray.create();

    items.forEach(function(item) {
      var filter = options.filter;
      if (filter) {
        var found = false;
        for (var i = 0; i < filterFields.length; ++i) {
          var filterField = filterFields[i];
          if (item[filterField].indexOf(filter) >= 0) {
            found = true;
            break;
          }
        }

        if (!found) {
          return;
        }
      }

      if (opt_extrafilter && !opt_extrafilter(item)) {
        return;
      }

      orderedItems.push(item);
    });

    orderedItems.entries.sort(function(a, b) {
      var left = a[options['predicate']];
      var right = b[options['predicate']];

      for (var i = 0; i < numericFields.length; ++i) {
        var numericField = numericFields[i];
        if (options['predicate'] == numericField) {
          left = left * 1;
          right = right * 1;
          break;
        }
      }

      if (left == null) {
        left = '0.00';
      }

      if (right == null) {
        right = '0.00';
      }

      if (left == right) {
        return 0;
      }

      return left > right ? -1 : 1;
    });

    if (options['reverse']) {
      orderedItems.entries.reverse();
    }

    orderedItems.setVisible(true);
    return orderedItems;
  };

  return tableService;
}]);