/**
 * An element which displays an avatar for the given avatar data.
 */
angular.module('quay').directive('avatar', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/avatar.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'data': '=data',
      'size': '=size'
    },
    controller: function($scope, $element, AvatarService, Config, UIService, $timeout) {
      $scope.AvatarService = AvatarService;
      $scope.Config = Config;
      $scope.isLoading = true;
      $scope.showGravatar = false;
      $scope.loadGravatar = false;

      $scope.imageCallback = function(result) {
        $scope.isLoading = false;

        if (!result) {
          $scope.showGravatar = false;
          return;
        }

        // Determine whether the gravatar is blank.
        var canvas = document.createElement("canvas");
        canvas.width = 512;
        canvas.height = 512;

        var ctx = canvas.getContext("2d");
        ctx.drawImage($element.find('img')[0], 0, 0);

        var blank = document.createElement("canvas");
        blank.width = 512;
        blank.height = 512;

        var isBlank = canvas.toDataURL('text/png') == blank.toDataURL('text/png');
        $scope.showGravatar = !isBlank;
      };

      $scope.$watch('size', function(size) {
        size = size * 1 || 16;
        $scope.fontSize = (size - 4) + 'px';
        $scope.lineHeight = size + 'px';
        $scope.imageSize = size;
      });

      $scope.$watch('data', function(data) {
        if (!data) { return; }

        $scope.loadGravatar = Config.AVATAR_KIND == 'gravatar' &&
          (data.kind == 'user' || data.kind == 'org');

        $scope.isLoading = $scope.loadGravatar;
        $scope.hasGravatar = false;
      });
    }
  };
  return directiveDefinitionObject;
});