/**
 * An element which displays a table of events on a repository and allows them to be
 * edited.
 */
angular.module('quay').directive('repositoryEventsTable', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/repository-events-table.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'repository': '=repository',
      'isEnabled': '=isEnabled'
    },
    controller: function($scope, $element, $timeout, ApiService, Restangular, UtilService,
                         ExternalNotificationData, $location, StateService, DocumentationService, $sanitize) {
      $scope.canCreateNotification = function() {
        return StateService.inReadOnlyMode()
          ? false
          : $scope.repository.state === 'MIRROR' || $scope.repository.can_write;
      };
      $scope.showNewNotificationCounter = 0;
      $scope.newNotificationData = {};
      $scope.DocumentationService = DocumentationService;

      var loadNotifications = function() {
        if (!$scope.repository || !$scope.isEnabled) { return; }

        var add_event = $location.search()['add_event'];
        if (add_event) {
          $timeout(function() {
            $scope.newNotificationData = {
              'currentEvent': ExternalNotificationData.getEventInfo(add_event)
            };

            $scope.askCreateNotification();
          }, 100);

          $location.search('add_event', null);
        }

        if ($scope.notificationsResource) {
          return;
        }

        var params = {
          'repository': $scope.repository.namespace + '/' + $scope.repository.name
        };

        $scope.notificationsResource = ApiService.listRepoNotificationsAsResource(params).get(
          function(resp) {
            $scope.notifications = resp.notifications;
            return $scope.notifications;
          });
      };

      $scope.$watch('repository', loadNotifications);
      $scope.$watch('isEnabled', loadNotifications);

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

      $scope.deleteNotification = function(notification) {
        var params = {
          'repository': $scope.repository.namespace + '/' + $scope.repository.name,
          'uuid': notification.uuid
        };

        ApiService.deleteRepoNotification(null, params).then(function() {
          var index = $.inArray(notification, $scope.notifications);
          if (index < 0) { return; }
          $scope.notifications.splice(index, 1);

          if (!$scope.repository._notificationCounter) {
            $scope.repository._notificationCounter = 0;
          }

          $scope.repository._notificationCounter++;

        }, ApiService.errorDisplay('Cannot delete notification'));
      };

      $scope.reenableNotification = function(notification) {
        var params = {
          'repository': $scope.repository.namespace + '/' + $scope.repository.name,
          'uuid': notification.uuid
        };

        ApiService.resetRepositoryNotificationFailures(null, params).then(function() {
          var index = $.inArray(notification, $scope.notifications);
          if (index < 0) { return; }
          $scope.notifications[index].number_of_failures = 0
        }, ApiService.errorDisplay('Cannot re-enable notification'));
      };


      $scope.showNotifyInfo = function(notification, field) {
        var dom = document.createElement('input');
        dom.setAttribute('type', 'text');
        dom.setAttribute('class', 'form-control');
        dom.setAttribute('value', notification.config[field]);
        dom.setAttribute('readonly', 'readonly');

        bootbox.dialog({
          'title': ($sanitize(notification.title) || 'Notification') + ' ' + field,
          'message': dom.outerHTML,
          'buttons': {
            "Done": {
              className: "btn-primary",
              callback: function() {}
            },
          }
        });
      };

      $scope.showWebhookInfo = function(notification) {
        var eventId = notification.event;
        document.location = $scope.DocumentationService.getUrl('notifications.webhook', {
          'event': eventId
        });
      };

      $scope.testNotification = function(notification) {
        var params = {
          'repository': $scope.repository.namespace + '/' + $scope.repository.name,
          'uuid': notification.uuid
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
        }, ApiService.errorDisplay('Could not issue test notification'));
      };

    }
  };
  return directiveDefinitionObject;
});