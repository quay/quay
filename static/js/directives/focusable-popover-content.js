/**
 * An element which, when used to display content inside a popover, hide the popover once
 * the content loses focus.
 */
angular.module('quay').directive('focusablePopoverContent', ['$timeout', '$popover', function ($timeout, $popover) {
  return {
    restrict: "A",
    link: function (scope, element, attrs) {
      $body = $('body');
      var hide = function() {
        $body.off('click');

        if (!scope) { return; }
        scope.$apply(function() {
          if (!scope || !scope.$hide) { return; }
          scope.$hide();
        });
      };

      scope.$on('$destroy', function() {
        $body.off('click');
      });

      $timeout(function() {
        $body.on('click', function(evt) {
          var target = evt.target;
          var isPanelMember = $(element).has(target).length > 0 || target == element;
          if (!isPanelMember) {
            hide();
          }
        });

        $(element).find('input').focus();
      }, 100);
    }
  };
}]);