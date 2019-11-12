/**
 * An element which displays a twitter message and author information.
 */
angular.module('quay').directive('twitterView', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/twitter-view.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'avatarUrl': '@avatarUrl',
      'authorName': '@authorName',
      'authorUser': '@authorUser',
      'messageUrl': '@messageUrl',
      'messageDate': '@messageDate'
    },
    controller: function($scope, $element) {
    }
  };
  return directiveDefinitionObject;
});