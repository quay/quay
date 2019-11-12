import billOfMaterials from "../../../bill-of-materials.json"

(function() {
  /**
   * About page.
   */
  angular.module('quayPages').config(['pages', function(pages) {
    pages.create('about', 'about.html', AboutCtrl, {
      'title': 'About Us',
      'description': 'About Us'
    });
  }]);

  function AboutCtrl($scope){
    $scope.billOfMaterials = billOfMaterials
  }
}());