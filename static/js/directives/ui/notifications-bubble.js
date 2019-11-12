/**
 * An element which displays the number and kind of application notifications. If there are no
 * notifications, then the element is hidden/empty.
 */
angular.module('quay').directive('notificationsBubble', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/notifications-bubble.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
    },
    controller: function($scope, UserService, NotificationService) {
      $scope.notificationService = NotificationService;
    }
  };
  return directiveDefinitionObject;
});
