/**
 * DEPRECATED: An element which displays controls and information about a defined external notification on
 * a repository.
 */
angular.module('quay').directive('externalNotificationView', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/external-notification-view.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'repository': '=repository',
      'notification': '=notification',
      'notificationDeleted': '&notificationDeleted'
    },
    controller: function($scope, $element, ExternalNotificationData, ApiService, DocumentationService) {
      $scope.DocumentationService = DocumentationService;
      $scope.deleteNotification = function() {
        var params = {
          'repository': $scope.repository.namespace + '/' + $scope.repository.name,
          'uuid': $scope.notification.uuid
        };

        ApiService.deleteRepoNotification(null, params).then(function() {
          $scope.notificationDeleted({'notification': $scope.notification});
        });
      };

      $scope.testNotification = function() {
        var params = {
          'repository': $scope.repository.namespace + '/' + $scope.repository.name,
          'uuid': $scope.notification.uuid
        };

        ApiService.testRepoNotification(null, params).then(function() {
          bootbox.dialog({
            "title": "Test Notification Queued",
            "message": "A test version of this notification has been queued and should appear shortly",
            "buttons": {
              "close": {
                "label": "Close",
                "className": "btn-primary"
              }
            }
          });
        });
      };

      $scope.$watch('notification', function(notification) {
        if (notification) {
          $scope.eventInfo = ExternalNotificationData.getEventInfo(notification.event);
          $scope.methodInfo = ExternalNotificationData.getMethodInfo(notification.method);
          $scope.config = notification.config;
        }
      });
    }
  };
  return directiveDefinitionObject;
});
