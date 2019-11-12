/**
 * Element for displaying the list of billing invoices for the user or organization.
 */
angular.module('quay').directive('billingInvoices', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/billing-invoices.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'organization': '=organization',
      'user': '=user',
      'makevisible': '=makevisible'
    },
    controller: function($scope, $element, $sce, ApiService) {
      $scope.loading = false;
      $scope.showCreateField = null;
      $scope.invoiceFields = [];

      var update = function() {
        var hasValidUser = !!$scope.user;
        var hasValidOrg = !!$scope.organization;
        var isValid = hasValidUser || hasValidOrg;

        if (!$scope.makevisible || !isValid) {
          return;
        }

        $scope.loading = true;

        ApiService.listInvoices($scope.organization).then(function(resp) {
          $scope.invoices = resp.invoices;
          $scope.loading = false;
        }, function() {
          $scope.invoices = [];
          $scope.loading = false;
        });

        ApiService.listInvoiceFields($scope.organization).then(function(resp) {
          $scope.invoiceFields = resp.fields || [];
        }, function() {
          $scope.invoiceFields = [];
        });
      };

      $scope.$watch('organization', update);
      $scope.$watch('user', update);
      $scope.$watch('makevisible', update);

      $scope.showCreateField = function() {
        $scope.createFieldInfo = {
          'title': '',
          'value': ''
        };
      };

      $scope.askDeleteField = function(field) {
        bootbox.confirm('Are you sure you want to delete field ' + field.title + '?', function(r) {
          if (r) {
            var params = {
              'field_uuid': field.uuid
            };

            ApiService.deleteInvoiceField($scope.organization, null, params).then(function(resp) {
              $scope.invoiceFields = $.grep($scope.invoiceFields, function(current) {
                return current.uuid != field.uuid
              });

            }, ApiService.errorDisplay('Could not delete custom field'));
          }
        });
      };

      $scope.createCustomField = function(title, value, callback) {
        var data = {
          'title': title,
          'value': value
        };

        if (!title || !value) {
          callback(false);
          bootbox.alert('Missing title or value');
          return;
        }

        ApiService.createInvoiceField($scope.organization, data).then(function(resp) {
          $scope.invoiceFields.push(resp);
          callback(true);
        }, ApiService.errorDisplay('Could not create custom field'));
      };
    }
  };

  return directiveDefinitionObject;
});

