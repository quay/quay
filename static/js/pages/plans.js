(function() {
  /**
   * The plans/pricing page.
   */
  angular.module('quayPages').config(['pages', function(pages) {
    pages.create('plans', 'plans.html', PlansCtrl, {
      'title': 'Plans and Pricing',
      'newLayout': true
    });
  }]);

  function PlansCtrl($scope) {}
})();