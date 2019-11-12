/**
 * An element which displays the settings panel for a repository view.
 */
angular.module('quay').directive('repoPanelSettings', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/repo-view/repo-panel-settings.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'repository': '=repository',
      'isEnabled': '=isEnabled'
    },
    controller: function($scope, $element, $route, ApiService, Config, Features, StateService) {
      StateService.updateStateIn($scope, function(state) {
        $scope.inReadOnlyMode = state.inReadOnlyMode;
      });

      $scope.Features = Features;
      $scope.deleteDialogCounter = 0;

      var getTitle = function(repo) {
        return repo.kind == 'application' ? 'application' : 'image';
      };

      $scope.getBadgeFormat = function(format, repository) {
        if (!repository) { return ''; }

        var imageUrl = Config.getUrl('/repository/' + repository.namespace + '/' + repository.name + '/status');
        if (!$scope.repository.is_public) {
          imageUrl += '?token=' + repository.status_token;
        }

        var linkUrl = Config.getUrl('/repository/' + repository.namespace + '/' + repository.name);

        switch (format) {
          case 'svg':
            return imageUrl;

          case 'md':
            return '[![Docker Repository on ' + Config.REGISTRY_TITLE_SHORT + '](' + imageUrl +
              ' "Docker Repository on ' + Config.REGISTRY_TITLE_SHORT  + '")](' + linkUrl + ')';

          case 'asciidoc':
            return 'image:' + imageUrl + '["Docker Repository on ' + Config.REGISTRY_TITLE_SHORT  + '", link="' + linkUrl + '"]';
        }

        return '';
      };

      $scope.askDelete = function() {
        $scope.deleteDialogCounter++;
        $scope.deleteRepoInfo = {
          'counter': $scope.deleteDialogCounter
        };
      };

      $scope.deleteRepo = function(info, callback) {
        var params = {
          'repository': $scope.repository.namespace + '/' + $scope.repository.name
        };

        var errorHandler = ApiService.errorDisplay(
          'Could not delete ' + getTitle($scope.repository), callback);

        ApiService.deleteRepository(null, params).then(function() {
          callback(true);
          setTimeout(function() {
            document.location = '/repository/';
          }, 100);
        }, errorHandler);
      };

      $scope.askChangeAccess = function(newAccess) {
        var msg = 'Are you sure you want to make this ' + getTitle($scope.repository) + ' ' +
                   newAccess + '?';

        bootbox.confirm(msg, function(r) {
          if (!r) { return; }
          $scope.changeAccess(newAccess);
        });
      };

      $scope.changeAccess = function(newAccess) {
        var visibility = {
          'visibility': newAccess
        };

        var params = {
          'repository': $scope.repository.namespace + '/' + $scope.repository.name
        };

        ApiService.changeRepoVisibility(visibility, params).then(function() {
          $scope.repository.is_public = newAccess == 'public';
        }, ApiService.errorDisplay('Could not change visibility'));
      };

      // Hide State, for now, if mirroring feature-flag is not enabled.
      if (Features.REPO_MIRROR) {
        $scope.repoStates = ['NORMAL', 'READ_ONLY'];
      }

      // Only show MIRROR as an option if the feature-flag is enabled.
      if (Features.REPO_MIRROR) { $scope.repoStates.push('MIRROR'); }

      // Hide State, for now, if mirroring feature-flag is not enabled.
      if (Features.REPO_MIRROR) {
        $scope.selectedState = $scope.repository.state;
        $scope.changeState = function() {
          let state = {'state': $scope.selectedState};
          let params = {'repository': $scope.repository.namespace + '/' + $scope.repository.name};
          ApiService.changeRepoState(state, params)
            .then(function() {
              $scope.repository.state = $scope.selectedState;
              $route.reload(); // State will eventually affect many UI elements. Reload the view.
            }, ApiService.errorDisplay('Could not change state'));
        }
      }
    }
  };
  return directiveDefinitionObject;
});
