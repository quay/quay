/**
 * An element which displays labels.
 */
angular.module('quay').directive('labelList', function () {
  return {
    templateUrl: '/static/directives/label-list.html',
    restrict: 'C',
    replace: true,
    scope: {
      expand: '@expand',
      labels: '<labels'
    },
    controller: function($scope) {}
  };
});
