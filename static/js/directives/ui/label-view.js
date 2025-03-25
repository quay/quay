/**
 * An element which displays a single label.
 */
angular.module('quay').directive('labelView', function () {
  return {
    templateUrl: '/static/directives/label-view.html',
    restrict: 'C',
    replace: true,
    scope: {
      expand: '@expand',
      label: '<label'
    },
    controller: function($scope, $sanitize) {
      $scope.getKind = function(label) {
        switch (label.media_type) {
          case 'application/json':
            return 'json';
        }

        return '';
      };

      $scope.isUrl = function(value) {
        return value && value.indexOf('https:') == 0;
      };

    }
  };
});
