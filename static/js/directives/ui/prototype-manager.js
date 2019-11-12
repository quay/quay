/**
 * Element for managing the prototype permissions for an organization.
 */
angular.module('quay').directive('prototypeManager', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/prototype-manager.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'organization': '=organization'
    },
    controller: function($scope, $element, ApiService, StateService) {
      $scope.inReadOnlyMode = StateService.inReadOnlyMode();
      $scope.loading = false;
      $scope.activatingForNew = null;
      $scope.delegateForNew = null;
      $scope.clearCounter = 0;
      $scope.newForWholeOrg = true;
      $scope.feedback = null;

      $scope.setRole = function(role, prototype) {
        var params = {
          'orgname': $scope.organization.name,
          'prototypeid': prototype.id
        };

        var data = {
          'id': prototype.id,
          'role': role
        };

        ApiService.updateOrganizationPrototypePermission(data, params).then(function(resp) {
          prototype.role = role;

          $scope.feedback = {
            'kind': 'success',
            'message': 'Role updated'
          };
        }, ApiService.errorDisplay('Cannot modify permission'));
      };

      $scope.comparePrototypes = function(p) {
        return p.activating_user ? p.activating_user.name : ' ';
      };

      $scope.setRoleForNew = function(role) {
        $scope.newRole = role;
      };

      $scope.setNewForWholeOrg = function(value) {
        $scope.newForWholeOrg = value;
      };

      $scope.showAddDialog = function() {
        $scope.activatingForNew = null;
        $scope.delegateForNew = null;
        $scope.newRole = 'read';
        $scope.clearCounter++;
        $scope.newForWholeOrg = true;
        $('#addPermissionDialogModal').modal({});
      };

      $scope.createPrototype = function() {
        $scope.loading = true;

        var params = {
          'orgname': $scope.organization.name
        };

        var data = {
          'delegate': $scope.delegateForNew,
          'role': $scope.newRole
        };

        if (!$scope.newForWholeOrg) {
          data['activating_user'] = $scope.activatingForNew;
        }

        var errorHandler = ApiService.errorDisplay('Cannot create permission',
                                                   function(resp) {
                                                     $('#addPermissionDialogModal').modal('hide');
                                                   });

        ApiService.createOrganizationPrototypePermission(data, params).then(function(resp) {
          $scope.prototypes.push(resp);
          $scope.loading = false;
          $('#addPermissionDialogModal').modal('hide');
        }, errorHandler);
      };

      $scope.deletePrototype = function(prototype) {
        $scope.loading = true;

        var params = {
          'orgname': $scope.organization.name,
          'prototypeid': prototype.id
        };

        ApiService.deleteOrganizationPrototypePermission(null, params).then(function(resp) {
          $scope.prototypes.splice($scope.prototypes.indexOf(prototype), 1);
          $scope.loading = false;

          $scope.feedback = {
            'kind': 'success',
            'message': 'Default Permission deleted'
          };
        }, ApiService.errorDisplay('Cannot delete permission'));
      };

      var update = function() {
        if (!$scope.organization) { return; }
        if ($scope.loading) { return; }

        var params = {'orgname': $scope.organization.name};

        $scope.loading = true;
        ApiService.getOrganizationPrototypePermissions(null, params).then(function(resp) {
          $scope.prototypes = resp.prototypes;
          $scope.loading = false;
        });
      };

      $scope.$watch('organization', update);
    }
  };
  return directiveDefinitionObject;
});