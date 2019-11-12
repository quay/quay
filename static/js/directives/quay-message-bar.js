/**
 * An element which displays a message for users to read.
 */
angular.module('quay').directive('quayMessageBar', function () {
  return {
    priority: 0,
    templateUrl: '/static/directives/quay-message-bar.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {},
    controller: function ($scope, $element, $rootScope, ApiService, NotificationService,
                          StateService) {
      $scope.messages = [];
      $scope.NotificationService = NotificationService;

      StateService.updateStateIn($scope, function(state) {
        $scope.inReadOnlyMode = state.inReadOnlyMode;
      });

      ApiService.getGlobalMessages().then(function (data) {
        $scope.messages = data['messages'] || [];
      }, function (resp) {
        return true;
      });
    }
  };
});
