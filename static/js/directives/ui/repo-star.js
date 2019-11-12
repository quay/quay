/**
 * An element that displays the star status of a repository and allows it to be toggled.
 */
angular.module('quay').directive('repoStar', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/repo-star.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      repository: '=repository',
      starToggled: '&starToggled'
    },
    controller: function($scope, $element, UserService, ApiService, StateService) {
      $scope.loggedIn = false;
      $scope.inReadOnlyMode = StateService.inReadOnlyMode();

      // Star a repository or unstar a repository.
      $scope.toggleStar = function() {
        if (StateService.inReadOnlyMode()) {
          return;
        }

        if ($scope.repository.is_starred) {
          unstarRepo();
        } else {
          starRepo();
        }
      };

      // Star a repository and update the UI.
      var starRepo = function() {
        var data = {
          'namespace': $scope.repository.namespace,
          'repository': $scope.repository.name
        };

        ApiService.createStar(data).then(function(result) {
          $scope.repository.is_starred = true;
          $scope.starToggled({'repository': $scope.repository});
        }, ApiService.errorDisplay('Could not star repository'));
      };

      // Unstar a repository and update the UI.
      var unstarRepo = function(repo) {
        var data = {
          'repository': $scope.repository.namespace + '/' + $scope.repository.name
        };

        ApiService.deleteStar(null, data).then(function(result) {
          $scope.repository.is_starred = false;
          $scope.starToggled({'repository': $scope.repository});
        }, ApiService.errorDisplay('Could not unstar repository'));
      };

      $scope.$watch('repository', function() {
        $scope.loggedIn = !UserService.currentUser().anonymous;
      });
    }
  };

  return directiveDefinitionObject;
});