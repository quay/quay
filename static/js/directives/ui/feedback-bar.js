/**
 * An element which displays a feedback bar when an action has been taken.
 */
angular.module('quay').directive('feedbackBar', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/feedback-bar.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'feedback': '=feedback'
    },
    controller: function($scope, $element, AvatarService, Config, UIService, $timeout, StringBuilderService) {
      $scope.viewCounter = 0;
      $scope.formattedMessage = '';

      $scope.$watch('feedback', function(feedback) {
        if (feedback) {
          $scope.formattedMessage = StringBuilderService.buildTrustedString(feedback.message, feedback.data || {}, 'span');
          $scope.viewCounter++;
        } else {
          $scope.viewCounter = 0;
        }
      });

      $($element).find('.feedback-bar-element')
                 .on('webkitAnimationEnd oanimationend oAnimationEnd msAnimationEnd animationend',
        function(e) {
          $scope.$apply(function() {
            $scope.viewCounter = 0;
          });
        });
    }
  };
  return directiveDefinitionObject;
});