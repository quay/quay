(function() {
  /**
   * Billing plans page.
   */
  angular.module('quayPages').config(['pages', function(pages) {
    pages.create('billing', 'billing.html', BillingCtrl, {
      'title': 'Billing',
      'description': 'Billing',
      'newLayout': true
    });
  }]);

  /**
   * Billing invoices page.
   */
  angular.module('quayPages').config(['pages', function(pages) {
    pages.create('invoices', 'invoices.html', BillingCtrl, {
      'title': 'Billing Invoices',
      'description': 'Billing Invoices',
      'newLayout': true
    });
  }]);


  function BillingCtrl($scope, ApiService, $routeParams, UserService) {
    $scope.orgname = $routeParams['orgname'];
    $scope.username = $routeParams['username'];

    var loadEntity = function() {
      if ($scope.orgname) {
        $scope.entityResource = ApiService.getOrganizationAsResource({'orgname': $scope.orgname}).get(function(org) {
          $scope.organization = org;
        });
      } else {
        UserService.updateUserIn($scope, function(currentUser) {
          $scope.entityResource = ApiService.getUserInformationAsResource({'username': $scope.username}).get(function(user) {
            $scope.invaliduser = !currentUser || currentUser.username != $scope.username;
            $scope.viewuser = user;
          });
        });
      }
    };

    // Load the user or organization.
    loadEntity();
  }
}());