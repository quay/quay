/**
 * An element for managing global messages.
 */
angular.module('quay').directive('globalMessageTab', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/global-message-tab.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'isEnabled': '=isEnabled'
    },
    controller: function ($scope, $element, ApiService, StateService) {
      $scope.inReadOnlyMode = StateService.inReadOnlyMode();

      $scope.newMessage = {
        'media_type': 'text/markdown',
        'severity': 'info'
      };
      $scope.creatingMessage = false;

      $scope.showCreateMessage = function () {
        $scope.createdMessage = null;
        $('#createMessageModal').modal('show');
      };

      $scope.createNewMessage = function () {
        if (StateService.inReadOnlyMode()) {
          return;
        }

        $scope.creatingMessage = true;
        $scope.createdMessage = null;

        var errorHandler = ApiService.errorDisplay('Cannot create message', function () {
          $scope.creatingMessage = false;
          $('#createMessageModal').modal('hide');
        });

        var data = {
          'message': $scope.newMessage
        };

        ApiService.createGlobalMessage(data, null).then(function (resp) {
          $scope.creatingMessage = false;

          $('#createMessageModal').modal('hide');
          $scope.loadMessageInternal();
        }, errorHandler)
      };
      
      $scope.updateMessage = function(content) {
        $scope.newMessage.content = content;
      };

      $scope.showDeleteMessage = function (uuid) {
        if (StateService.inReadOnlyMode()) {
          return;
        }

        $scope.messageToDelete = uuid;
        $('#confirmDeleteMessageModal').modal({});
      };

      $scope.deleteMessage = function (uuid) {
        if (StateService.inReadOnlyMode()) {
          return;
        }

        $('#confirmDeleteMessageModal').modal('hide');
        ApiService.deleteGlobalMessage(null, {uuid: uuid}).then(function (resp) {
          $scope.loadMessageInternal();
        }, ApiService.errorDisplay('Can not delete message'));
      };

      $scope.loadMessageOfTheDay = function () {
        if ($scope.messages) {
          return;
        }

        $scope.loadMessageInternal();
      };

      $scope.loadMessageInternal = function () {
        ApiService.getGlobalMessages().then(function (resp) {
          $scope.messages = resp['messages'];
        }, function (resp) {
          $scope.messages = [];
          $scope.messagesErrors = ApiService.getErrorMessage(resp);
        });
      };

      $scope.$watch('isEnabled', function (value) {
        if (value) {
          $scope.loadMessageInternal();
        }
      });
    }
  };
  return directiveDefinitionObject;
});
