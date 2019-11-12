

const corStepBarUrl = require('./cor-step-bar.html');
const corStepUrl = require('./cor-step.html');
const corProgressBarUrl = require('./cor-progress-bar.html');

angular.module('quay-config')
    .directive('corStepBar', () => {
        const directiveDefinitionObject = {
            priority: 4,
            templateUrl: corStepBarUrl,
            replace: true,
            transclude: true,
            restrict: 'C',
            scope: {
                'progress': '=?progress'
            },
            controller: function($rootScope, $scope, $element) {
                $scope.$watch('progress', function(progress) {
                    if (!progress) { return; }

                    var index = 0;
                    for (var i = 0; i < progress.length; ++i) {
                        if (progress[i]) {
                            index = i;
                        }
                    }

                    $element.find('.transclude').children('.co-step-element').each(function(i, elem) {
                        $(elem).removeClass('active');
                        if (i <= index) {
                            $(elem).addClass('active');
                        }
                    });
                });
            }
        };
        return directiveDefinitionObject;
    })

    .directive('corStep', function() {
        var directiveDefinitionObject = {
            priority: 4,
            templateUrl: corStepUrl,
            replace: true,
            transclude: false,
            requires: '^corStepBar',
            restrict: 'C',
            scope: {
                'icon': '@icon',
                'title': '@title',
                'text': '@text'
            },
            controller: function($rootScope, $scope, $element) {
            }
        };
        return directiveDefinitionObject;
    })

    .directive('corProgressBar', function() {
        var directiveDefinitionObject = {
            priority: 4,
            templateUrl: corProgressBarUrl,
            replace: true,
            transclude: true,
            restrict: 'C',
            scope: {
                'progress': '=progress'
            },
            controller: function($rootScope, $scope, $element) {
            }
        };
        return directiveDefinitionObject;
    });
