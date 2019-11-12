(function() {
  /**
   * Security page.
   */
  angular.module('quayPages').config(['pages', function(pages) {
    pages.create('security', 'security.html', null, {
      'title': 'Security'
    });
  }]);
}());