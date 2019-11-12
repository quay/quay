const loaderUrl = require('./cor-loader.html');
const inlineUrl = require('./cor-loader-inline.html');

angular.module('quay-config')
    .directive('corLoader', function() {
        var directiveDefinitionObject = {
            templateUrl: loaderUrl,
            replace: true,
            restrict: 'C',
            scope: {
            },
            controller: function($rootScope, $scope, $element) {
            }
        };
        return directiveDefinitionObject;
    })
    .directive('corLoaderInline', function() {
        var directiveDefinitionObject = {
            templateUrl: inlineUrl,
            replace: true,
            restrict: 'C',
            scope: {
            },
            controller: function($rootScope, $scope, $element) {
            }
        };
        return directiveDefinitionObject;
    });
