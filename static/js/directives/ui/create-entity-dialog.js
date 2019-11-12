/**
 * An element which displays a create entity dialog.
 */
angular.module('quay').directive('createEntityDialog', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/create-entity-dialog.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'info': '=info',

      'entityKind': '@entityKind',
      'entityTitle': '@entityTitle',
      'entityIcon': '@entityIcon',
      'entityNameRegex': '@entityNameRegex',
      'allowEntityDescription': '@allowEntityDescription',

      'entityCreateRequested': '&entityCreateRequested',
      'entityCreateCompleted': '&entityCreateCompleted'
    },

    controller: function($scope, $element, ApiService, UIService, UserService) {
      $scope.context = {
        'setPermissionsCounter': 0
      };

      $scope.$on('$destroy', function() {
        if ($scope.inBody) {
          document.body.removeChild($element[0]);
        }
      });

      $scope.hide = function() {
        $element.find('.modal').modal('hide');
        if ($scope.entity) {
          $scope.entityCreateCompleted({'entity': $scope.entity});
          $scope.entity = null;
        }
      };

      $scope.show = function() {
        $scope.entityName = null;
        $scope.entityDescription = null;
        $scope.entity = null;
        $scope.entityForPermissions = null;
        $scope.creating = false;
        $scope.view = 'enterName';
        $scope.enterNameForm.$setPristine(true);

        // Move the dialog to the body to prevent it from nesting if called
        // from within another dialog.
        $element.find('.modal').modal({});
        $scope.inBody = true;
        document.body.appendChild($element[0]);
      };

      var entityCreateCallback = function(entity) {
        $scope.entity = entity;

        if (!entity || $scope.info.skip_permissions) {
          $scope.hide();
          return;
        }
      };

      $scope.createEntity = function() {
        $scope.view = 'creating';
        $scope.entityCreateRequested({
          'name': $scope.entityName,
          'description': $scope.entityDescription,
          'callback': entityCreateCallback
        });
      };

      $scope.permissionsSet = function(repositories) {
        $scope.entity['repo_count'] = repositories.length;
        $scope.hide();
      };

      $scope.settingPermissions = function() {
        $scope.view = 'settingperms';
      };

      $scope.setPermissions = function() {
        $scope.context.setPermissionsCounter++;
      };

      $scope.repositoriesLoaded = function(repositories) {
        if (repositories && !repositories.length) {
          $scope.hide();
          return;
        }

        $scope.view = 'setperms';
      };

      $scope.$watch('entityNameRegex', function(r) {
        if (r) {
          $scope.entityNameRegexObj = new RegExp(r);
        }
      });

      $scope.$watch('info', function(info) {
        if (!info || !info.namespace) {
          $scope.hide();
          return;
        }

        $scope.namespace = UserService.getNamespace(info.namespace);
        if ($scope.namespace) {
          $scope.show();
        }
      });
    }
  };
  return directiveDefinitionObject;
});