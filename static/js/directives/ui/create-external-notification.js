/**
 * An element which displays a form to register a new external notification on a repository.
 */
angular.module('quay').directive('createExternalNotification', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/create-external-notification.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'repository': '=repository',
      'notificationCreated': '&notificationCreated',
      'defaultData': '=defaultData'
    },
    controller: function($scope, $element, ExternalNotificationData, ApiService, $timeout, StringBuilderService) {
      $scope.currentEvent = null;
      $scope.currentMethod = null;
      $scope.status = '';
      $scope.currentConfig = {};
      $scope.currentEventConfig = {};
      $scope.clearCounter = 0;
      $scope.unauthorizedEmail = false;

      $scope.events = ExternalNotificationData.getSupportedEvents();
      $scope.methods = ExternalNotificationData.getSupportedMethods();

      $scope.getPattern = function(field) {
        if (field._cached_regex) {
          return field._cached_regex;
        }

        field._cached_regex = new RegExp(field.pattern);
        return field._cached_regex;
      };

      $scope.setEvent = function(event) {
        $scope.currentEvent = event;
        $scope.currentEventConfig = {};
      };

      $scope.setMethod = function(method) {
        $scope.currentConfig = {};
        $scope.currentMethod = method;
        $scope.unauthorizedEmail = false;
      };

      $scope.hasRegexMismatch = function(err, fieldName) {
        if (!err.pattern) {
          return;
        }

        for (var i = 0; i < err.pattern.length; ++i) {
          var current = err.pattern[i];
          var value = current.$viewValue;
          var elem = $element.find('#' + fieldName);
          if (value == elem[0].value) {
            return true;
          }
        }

        return false;
      };

      $scope.createNotification = function() {
        if (!$scope.currentConfig.email) {
          $scope.performCreateNotification();
          return;
        }

        $scope.status = 'checking-email';
        $scope.checkEmailAuthorization();
      };

      $scope.checkEmailAuthorization = function() {
        var params = {
          'repository': $scope.repository.namespace + '/' + $scope.repository.name,
          'email': $scope.currentConfig.email
        };

        ApiService.checkRepoEmailAuthorized(null, params).then(function(resp) {
          $scope.handleEmailCheck(resp.confirmed);
        }, function(resp) {
          $scope.handleEmailCheck(false);
        });
      };

      $scope.performCreateNotification = function() {
        $scope.status = 'creating';

        var params = {
          'repository': $scope.repository.namespace + '/' + $scope.repository.name
        };

        var data = {
          'event': $scope.currentEvent.id,
          'method': $scope.currentMethod.id,
          'config': $scope.currentConfig,
          'eventConfig': $scope.currentEventConfig,
          'title': $scope.currentTitle
        };

        ApiService.createRepoNotification(data, params).then(function(resp) {
          $scope.status = '';
          $scope.notificationCreated({'notification': resp});
        }, function(resp) {
          $scope.status = 'error';
          $scope.errorMessage = ApiService.getErrorMessage(resp, 'Could not create notification');
        });
      };

      $scope.handleEmailCheck = function(isAuthorized) {
        if (isAuthorized) {
          $scope.performCreateNotification();
          return;
        }

        if ($scope.status == 'authorizing-email-sent') {
          $scope.watchEmail();
        } else {
          $scope.status = 'unauthorized-email';
        }

        $scope.unauthorizedEmail = true;
        $('#authorizeEmailModal').modal({});
      };

      $scope.sendAuthEmail = function() {
        $scope.status = 'authorizing-email';

        var params = {
          'repository': $scope.repository.namespace + '/' + $scope.repository.name,
          'email': $scope.currentConfig.email
        };

        ApiService.sendAuthorizeRepoEmail(null, params).then(function(resp) {
          $scope.status = 'authorizing-email-sent';
          $scope.watchEmail();
        });
      };

      $scope.watchEmail = function() {
        // TODO: change this to SSE?
        $timeout(function() {
          $scope.checkEmailAuthorization();
        }, 1000);
      };

      $scope.cancelEmailAuth = function() {
        $scope.status = '';
        $('#authorizeEmailModal').modal('hide');
      };

      $scope.getHelpUrl = function(field, config) {
        var helpUrl = field['help_url'];
        if (!helpUrl) {
          return null;
        }

        return StringBuilderService.buildUrl(helpUrl, config);
      };

      $scope.$watch('defaultData', function(counter) {
        if ($scope.defaultData && $scope.defaultData['currentEvent']) {
          $scope.setEvent($scope.defaultData['currentEvent']);
        }
      });
    }
  };
  return directiveDefinitionObject;
});


