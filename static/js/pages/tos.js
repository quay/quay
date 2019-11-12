(function() {
  /**
   * TOS page.
   */
  angular.module('quayPages').config(['pages', function(pages) {
    pages.create('tos', 'tos.html', null, {
      'title': 'Terms of Service'
    });
  }]);
}());