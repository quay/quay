// From: https://github.com/angular/angular.js/issues/6726#issuecomment-116251130
angular.module('quay').directive('rangeSlider', [function () {
    return {
        replace: true,
        restrict: 'E',
        require: 'ngModel',
        template: '<input type="range"/>',
        link: function (scope, element, attrs, ngModel) {
            var ngRangeMin;
            var ngRangeMax;
            var ngRangeStep;
            var value;

            function init() {
                if (!angular.isDefined(attrs.ngRangeMin)) {
                    ngRangeMin = 0;
                } else {
                    scope.$watch(attrs.ngRangeMin, function (newValue, oldValue, scope) {
                        if (angular.isDefined(newValue)) {
                            ngRangeMin = newValue;
                            setValue();
                        }
                    });
                }
                if (!angular.isDefined(attrs.ngRangeMax)) {
                    ngRangeMax = 100;
                } else {
                    scope.$watch(attrs.ngRangeMax, function (newValue, oldValue, scope) {
                        if (angular.isDefined(newValue)) {
                            ngRangeMax = newValue;
                            setValue();
                        }
                    });
                }
                if (!angular.isDefined(attrs.ngRangeStep)) {
                    ngRangeStep = 1;
                } else {
                    scope.$watch(attrs.ngRangeStep, function (newValue, oldValue, scope) {
                        if (angular.isDefined(newValue)) {
                            ngRangeStep = newValue;
                            setValue();
                        }
                    });
                }
                if (!angular.isDefined(ngModel)) {
                    value = 50;
                } else {
                    scope.$watch(
                        function () {
                            return ngModel.$modelValue;
                        },
                        function (newValue, oldValue, scope) {
                            if (angular.isDefined(newValue)) {
                                value = newValue;
                                setValue();
                            }
                        }
                    );
                }

                if (!ngModel) {
                    return;
                }
                ngModel.$parsers.push(function (value) {
                    var val = Number(value);
                    if (val !== val) {
                        val = undefined;
                    }
                    return val;
                });
            }

            function setValue() {
                if (
                    angular.isDefined(ngRangeMin) &&
                    angular.isDefined(ngRangeMax) &&
                    angular.isDefined(ngRangeStep) &&
                    angular.isDefined(value)
                    ) {
                    element.attr("min", ngRangeMin);
                    element.attr("max", ngRangeMax);
                    element.attr("step", ngRangeStep);
                    element.val(value);
                }
            }

            function read() {
                if (angular.isDefined(ngModel)) {
                    ngModel.$setViewValue(value);
                }
            }

            element.on('change', function () {
                if (angular.isDefined(value) && (value != element.val())) {
                    value = element.val();
                    scope.$apply(read);
                }
            });

            init();
        }
    };
}
]);