/**
 * Sets the 'filePresent' value on the scope if a file on the marked <input type="file"> exists.
 */
angular.module('quay').directive("filePresent", [function () {
  return {
    restrict: 'A',
    scope: {
      'filePresent': "="
    },
    link: function (scope, element, attributes) {
      element.bind("change", function (changeEvent) {
        scope.$apply(function() {
          scope.filePresent = changeEvent.target.files.length > 0;
        });
      });
    }
  }
}]);

/**
 * Raises the 'filesChanged' event on the scope if a file on the marked <input type="file"> exists.
 */
angular.module('quay').directive("filesChanged", [function () {
  return {
    restrict: 'A',
    scope: {
      'filesChanged': "&"
    },
    link: function (scope, element, attributes) {
      element.bind("change", function (changeEvent) {
        scope.$apply(function() {
          scope.filesChanged({'files': changeEvent.target.files});
        });
      });
    }
  }
}]);