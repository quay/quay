/**
 * An element which displays a summary of events on a repository of a particular type.
 */
angular.module('quay').directive('repositoryEventsSummary', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/repository-events-summary.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'repository': '=repository',
      'isEnabled': '=isEnabled',
      'eventFilter': '@eventFilter',
      'hasEvents': '=hasEvents'
    },
    controller: function($scope, ApiService, ExternalNotificationData) {
      var loadNotifications = function() {
        if (!$scope.repository || !$scope.isEnabled || !$scope.eventFilter || $scope.notificationsResource) {
          return;
        }

        var params = {
          'repository': $scope.repository.namespace + '/' + $scope.repository.name
        };

        $scope.notificationsResource = ApiService.listRepoNotificationsAsResource(params).get(
          function(resp) {
            var notifications = [];
            resp.notifications.forEach(function(notification) {
              if (notification.event == $scope.eventFilter) {
                notifications.push(notification);
              }
            });

            $scope.notifications = notifications;
            $scope.hasEvents = !!notifications.length;
            return $scope.notifications;
          });
      };

      $scope.$watch('repository', loadNotifications);
      $scope.$watch('isEnabled', loadNotifications);
      $scope.$watch('eventFilter', loadNotifications);

      // Watch _notificationCounter, which is set by create-external-notification-dialog. We use this
      // to invalidate and reload.
      $scope.$watch('repository._notificationCounter', function() {
        $scope.notificationsResource = null;
        loadNotifications();
      });

      loadNotifications();

      $scope.findEnumValue = function(values, index) {
        var found = null;
        Object.keys(values).forEach(function(key) {
          if (values[key]['index'] == index) {
            found = values[key];
            return
          }
        });

        return found
      };

      $scope.getEventInfo = function(notification) {
        return ExternalNotificationData.getEventInfo(notification.event);
      };

      $scope.getMethodInfo = function(notification) {
        return ExternalNotificationData.getMethodInfo(notification.method);
      };
    }
  };
  return directiveDefinitionObject;
});