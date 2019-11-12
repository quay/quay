/**
 * Adds an onresize event attribute that gets invokved when the size of the window changes.
 */
angular.module('quay').directive('onresize', function ($window, $parse, $timeout) {
  return function (scope, element, attr) {
    var fn = $parse(attr.onresize);

    var notifyResized = function() {
      // Angular.js enforces only one call to $apply can run at a time.
      // Use $timeout to make the scope update safe, even when called within another $apply block,
      // by scheduling it on the call stack.
      // See docs: https://docs.angularjs.org/error/$rootScope/inprog
      $timeout(function () {
        fn(scope);
      }, 0);
    };

    angular.element($window).on('resize', null, notifyResized);

    scope.$on('$destroy', function() {
      angular.element($window).off('resize', null, notifyResized);
    });
  };
});
