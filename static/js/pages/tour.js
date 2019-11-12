(function() {
  /**
   * The site tour page.
   */
  angular.module('quayPages').config(['pages', function(pages) {
    pages.create('tour', 'tour.html', TourCtrl, {
      'title': 'Feature Tour',
      'description': 'Take a tour of Quay\'s features'
    });
  }]);

  function TourCtrl($scope, $location) {
    $scope.kind = $location.path().substring('/tour/'.length);
  }
})();