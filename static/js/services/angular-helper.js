/**
 * Helper code for working with angular.
 */
angular.module('quay').factory('AngularHelper', [function($routeProvider) {
  var helper = {};

  helper.buildConditionalLinker = function($animate, name, evaluator) {
    // Based off of a solution found here: http://stackoverflow.com/questions/20325480/angularjs-whats-the-best-practice-to-add-ngif-to-a-directive-programmatically
    return function ($scope, $element, $attr, ctrl, $transclude) {
      var block;
      var childScope;
      var roles;

      $attr.$observe(name, function (value) {
        if (evaluator($scope.$eval(value))) {
          if (!childScope) {
            childScope = $scope.$new();
            $transclude(childScope, function (clone) {
              block = {
                startNode: clone[0],
                endNode: clone[clone.length++] = document.createComment(' end ' + name + ': ' + $attr[name] + ' ')
              };
              $animate.enter(clone, $element.parent(), $element);
            });
          }
        } else {
          if (childScope) {
            childScope.$destroy();
            childScope = null;
          }

          if (block) {
            $animate.leave(getBlockElements(block));
            block = null;
          }
        }
      });
    }
  };

  return helper;
}]);
