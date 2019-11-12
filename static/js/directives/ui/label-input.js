/**
 * An element which allows for editing labels.
 */
angular.module('quay').directive('labelInput', function () {
  return {
    templateUrl: '/static/directives/label-input.html',
    restrict: 'C',
    replace: true,
    scope: {
      'labels': '<labels',
      'updatedLabels': '=?updatedLabels',
    },
    controller: function($scope) {
      $scope.tags = [];

      $scope.$watch('tags', function(tags) {
        if (!tags) { return; }
        $scope.updatedLabels = tags.filter(function(tag) {
          parts = tag['keyValue'].split('=', 2);
          return tag['label'] ? tag['label'] : {
            'key': parts[0],
            'value': parts[1],
            'is_new': true
          };
        });
      }, true);

      $scope.$watch('labels', function(labels) {
        $scope.filteredLabels = labels.filter(function(label) {
          return label['source_type'] == 'api';
        });

        $scope.tags = $scope.filteredLabels.map(function(label) {
          return {
            'id': label['id'],
            'keyValue': label['key'] + '=' + label['value'],
            'label': label
          };
        });
      });
    }
  };
});
