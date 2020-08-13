
const titleUrl = require('./cor-title.html');
const titleContentUrl = require('./cor-title-content.html');

angular.module('quay-config')
    .directive('corTitleContent', function() {
        var directiveDefinitionObject = {
            priority: 1,
            templateUrl: titleContentUrl,
            replace: true,
            transclude: true,
            restrict: 'C',
            scope: {},
            controller: function($rootScope, $scope, $element) {
            }
        };
        return directiveDefinitionObject;
    })
    .directive('corTitle', function() {
        var directiveDefinitionObject = {
            priority: 1,
            templateUrl: titleUrl,
            replace: true,
            transclude: true,
            restrict: 'C',
            scope: {},
            controller: function($rootScope, $scope, $element) {
            }
        };
        return directiveDefinitionObject;
    });
