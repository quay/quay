/**
  * An element which allows for editing intervals.
  */
angular.module('quay').directive('intervalInput', function () {
  return {
    templateUrl: '/static/directives/interval-input.html',
    controllerAs: 'vm',
    replace: true,
    scope: {
      'seconds': '=seconds',
    },
    restrict: 'C',
    controller: function($scope) {

      let vm = this;

      vm.seconds = null;
      vm.selectedPeriod = null;
      vm.quantity = null;

      vm.periods = [
        { 'label': 'seconds', 'seconds': 1 },
        { 'label': 'minutes', 'seconds': 60 },
        { 'label': 'hours',   'seconds': 60 * 60 },
        { 'label': 'days',    'seconds': 60 * 60 * 24 },
        { 'label': 'weeks',   'seconds': 60 * 60 * 24 * 7 }
      ]

      let findMatchingPeriod = function(seconds) {
        for (let i = vm.periods.length - 1; i >= 0; i--) {
          let period = vm.periods[i];
          if (seconds % period.seconds == 0) {
            return period;
          }
        }

        return vm.periods[0]; // Fall-back to seconds if no matching period was found.
      }

      let calculateQuantity = function(seconds, secondsInPeriod) {
        if (seconds == 0) { return 0; }
        return seconds / secondsInPeriod;
      }

      vm.updateSeconds = function() {
        vm.seconds = vm.quantity * vm.selectedPeriod.seconds;
        $scope.seconds = vm.seconds;
      }

      $scope.$watch('seconds', function(newValue, oldValue) {

        if (vm.selectedPeriod == null) {
          vm.selectedPeriod = vm.periods[0];
        }

        if (newValue == NaN) {
          vm.seconds = 0;
          $scope.seconds = vm.seconds;
        }

        if (newValue !== oldValue) {
          vm.seconds = newValue;
          vm.selectedPeriod = findMatchingPeriod(vm.seconds);
          vm.quantity = calculateQuantity(vm.seconds, vm.selectedPeriod.seconds);
        }

      });
    }
  };
});