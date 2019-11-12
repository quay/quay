(function() {
  /**
   * DEPRECATED: Page which displays the list of organizations of which the user is a member.
   */
  angular.module('quayPages').config(['pages', function(pages) {
    pages.create('organizations', 'organizations.html', OrgsCtrl, {
      'title': 'View Organizations',
      'description': 'View and manage your organizations'
    });
  }]);

  function OrgsCtrl($scope, UserService) {
    UserService.updateUserIn($scope);
    browserchrome.update();
  }
})();