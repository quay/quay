const corOption = require('./cor-option.html');
const corOptionsMenu = require('./cor-options-menu.html');

angular.module('quay-config')
    .directive('corOptionsMenu', function() {
        var directiveDefinitionObject = {
            priority: 1,
            templateUrl: corOptionsMenu,
            replace: true,
            transclude: true,
            restrict: 'C',
            scope: {},
            controller: function($rootScope, $scope, $element) {
            }
        };
        return directiveDefinitionObject;
    })
    .directive('corOption', function() {
        var directiveDefinitionObject = {
            priority: 1,
            templateUrl: corOption,
            replace: true,
            transclude: true,
            restrict: 'C',
            scope: {
                'optionClick': '&optionClick'
            },
            controller: function($rootScope, $scope, $element) {
            }
        };
        return directiveDefinitionObject;
    });
