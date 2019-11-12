(function() {
  /**
   * Privacy page.
   */
  angular.module('quayPages').config(['pages', function(pages) {
    pages.create('privacy', 'privacy.html', null, {
      'title': 'Privacy Policy'
    });
  }]);
}());