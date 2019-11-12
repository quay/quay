/**
 * An element which displays a datetime picker.
 */
angular.module('quay').directive('datetimePicker', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/datetime-picker.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'datetime': '=datetime',
    },
    controller: function($scope, $element) {
      var datetimeSet = false;

       $(function() {
         $element.find('input').datetimepicker({
           'format': 'LLL',
           'sideBySide': true,
           'showClear': true,
           'minDate': new Date(),
           'debug': false
         });

         $element.find('input').on("dp.change", function (e) {
            $scope.$apply(function() {
              $scope.datetime = e.date ? e.date.unix() : null;
            });
         });
       });

       $scope.$watch('selected_datetime', function(value) {
         if (!datetimeSet) { return; }

         if (!value) {
           if ($scope.datetime) {
             $scope.datetime = null;
           }
           return;
         }

         $scope.datetime = (new Date(value)).getTime()/1000;
       });

      $scope.$watch('datetime', function(value) {
        if (!value) {
          $scope.selected_datetime = null;
          datetimeSet = true;
          return;
        }

        $scope.selected_datetime = moment.unix(value).format('LLL');
        datetimeSet = true;
    });
    }
  };
  return directiveDefinitionObject;
});