/**
 * An element which displays an application notification's information.
 */
angular.module('quay').directive('notificationView', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/notification-view.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'notification': '=notification',
      'parent': '=parent'
    },
    controller: function($scope, $element, $window, $location, UserService, NotificationService,
                         ApiService, StateService) {
      $scope.inReadOnlyMode = StateService.inReadOnlyMode();
      $scope.dismissing = false;

      var stringStartsWith = function (str, prefix) {
        return str.slice(0, prefix.length) == prefix;
      };

      $scope.getMessage = function(notification) {
        return NotificationService.getMessage(notification);
      };

      $scope.getAvatar = function(orgname) {
        var organization = UserService.getOrganization(orgname);
        if (!organization) { return ''; }

        return organization['avatar'] || '';
      };

      $scope.parseDate = function(dateString) {
        return Date.parse(dateString);
      };

      $scope.showNotification = function() {
        var url = NotificationService.getPage($scope.notification);
        if (url) {
          if (stringStartsWith(url, 'http://') || stringStartsWith(url, 'https://')) {
            $window.location.href = url;
          } else {
            var parts = url.split('?')
            $location.path(parts[0]);

            if (parts.length > 1) {
              $location.search(parts[1]);
            }

            $scope.parent.$hide();
          }
        }
      };

      $scope.dismissNotification = function(notification) {
        $scope.dismissing = true;
        NotificationService.dismissNotification(notification);
      };

      $scope.canDismiss = function(notification) {
        return NotificationService.canDismiss(notification);
      };

      $scope.getClass = function(notification) {
        return NotificationService.getClass(notification);
      };

      $scope.getActions = function(notification) {
        return NotificationService.getActions(notification);
      };
    }
  };
  return directiveDefinitionObject;
});
