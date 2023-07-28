const templateUrl = require('./cor-floating-bottom-bar.html');

angular.module('quay-config')
    .directive('corFloatingBottomBar', function() {
        var directiveDefinitionObject = {
            priority: 3,
            templateUrl,
            replace: true,
            transclude: true,
            restrict: 'C',
            scope: {},
            controller: function($rootScope, $scope, $element, $timeout, $interval) {
                var handler = function() {
                    $element.removeClass('floating');
                    $element.css('width', $element[0].parentNode.clientWidth + 'px');

                    var windowHeight = $(window).height();
                    var rect = $element[0].getBoundingClientRect();
                    if (rect.bottom > windowHeight) {
                        $element.addClass('floating');
                    }
                };

                $(window).on("scroll", handler);
                $(window).on("resize", handler);

                var previousHeight = $element[0].parentNode.clientHeight;
                var stop = $interval(function() {
                    var currentHeight = $element[0].parentNode.clientWidth;
                    if (previousHeight != currentHeight) {
                        currentHeight = previousHeight;
                        handler();
                    }
                }, 100);

                $scope.$on('$destroy', function() {
                    $(window).off("resize", handler);
                    $(window).off("scroll", handler);
                    $interval.cancel(stop);
                });
            }
        };
        return directiveDefinitionObject;
    });
