/**
 * Raises the 'filesChanged' event on the scope if a file on the marked <input type="file"> exists.
 */
angular.module('quay-config').directive("filesChanged", [function () {
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
