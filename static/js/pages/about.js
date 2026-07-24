(function() {
  /**
   * About page.
   */
  angular.module('quayPages').config(['pages', function(pages) {
    pages.create('about', 'about.html', null, {
      'title': 'About Us',
      'description': 'About Us'
    });
  }]);
}());
