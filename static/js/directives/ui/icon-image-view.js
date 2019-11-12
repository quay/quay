/**
 * An element which displays either an icon or an image, depending on the value.
 */
angular.module('quay').directive('iconImageView', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/icon-image-view.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'value': '@value'
    },
    controller: function($scope, $element) {
    }
  };
  return directiveDefinitionObject;
});
