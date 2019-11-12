/**
 * An element which displays a dialog for manually starting a dockerfile build.
 */
angular.module('quay').directive('dockerfileBuildDialog', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/dockerfile-build-dialog.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'repository': '=repository',
      'showNow': '=showNow',
      'buildStarted': '&buildStarted'
    },
    controller: function($scope, $element, ApiService) {
      $scope.viewTriggers = false;
      $scope.triggers = null;
      $scope.viewCounter = 0;

      $scope.startTriggerCounter = 0;
      $scope.startTrigger = null;

      $scope.showTriggers = function(value) {
        $scope.viewTriggers = value;
      };

      $scope.runTriggerNow = function(trigger) {
        $element.find('.dockerfilebuildModal').modal('hide');
        $scope.startTrigger = trigger;
        $scope.startTriggerCounter++;
      };

      $scope.startBuild = function() {
        $scope.buildStarting = true;
        $scope.startBuildCallback(function(status, messageOrBuild) {
          $element.find('.dockerfilebuildModal').modal('hide');
          if (status) {
            $scope.buildStarted({'build': messageOrBuild});
          } else {
            bootbox.alert(messageOrBuild || 'Could not start build');
          }
        });
      };

      $scope.readyForBuild = function(startBuild) {
        $scope.startBuildCallback = startBuild;
      };

      $scope.$watch('showNow', function(sn) {
        if (sn && $scope.repository) {
          $scope.viewTriggers = false;
          $scope.startTrigger = null;
          $scope.buildStarting = false;
          $scope.viewCounter++;

          $element.find('.dockerfilebuildModal').modal({});

          // Load the triggers (if necessary).
          if (!$scope.repository || !$scope.repository.can_admin) {
            $scope.triggersResource = null;
            $scope.triggers = null;
            return;
          }

          var params = {
            'repository': $scope.repository.namespace + '/' + $scope.repository.name
          };

          $scope.triggersResource = ApiService.listBuildTriggersAsResource(params).get(function(resp) {
            $scope.triggers = resp.triggers;
            $scope.viewTriggers = $scope.triggers.length > 0;
          });
        }
      });
    }
  };
  return directiveDefinitionObject;
});