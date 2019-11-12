/**
 * An element which displays a form for manually starting a dockerfile build.
 */
angular.module('quay').directive('dockerfileBuildForm', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/dockerfile-build-form.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'repository': '=repository',
      'isReady': '=?isReady',
      'reset': '=?reset',
      'readyForBuild': '&readyForBuild'
    },
    controller: function($scope, $element, ApiService, DockerfileService, Config) {
      $scope.state = 'empty';

      var checkPrivateImage = function(baseImage) {
        var params = {
          'repository': baseImage
        };

        $scope.state = 'checking-image';
        ApiService.getRepo(null, params).then(function(repository) {
          $scope.privateBaseRepository = repository.is_public ? null : baseImage;
          $scope.state = repository.is_public ? 'ready' : 'awaiting-bot';
        }, function() {
          $scope.privateBaseRepository = null;
          $scope.state = 'ready';
        });
      };

      $scope.handleFilesSelected = function(files, opt_callback) {
        $scope.pullEntity = null;
        $scope.state = 'checking';
        $scope.selectedFiles = files;

        DockerfileService.getDockerfile(files[0])
          .then(function(dockerfileInfo) {
            var baseImage = dockerfileInfo.getRegistryBaseImage();
            if (baseImage) {
              checkPrivateImage(baseImage);
            } else {
              $scope.state = 'ready';
            }

            $scope.$apply(function() {
              opt_callback && opt_callback(true, 'Dockerfile found and valid')
            });
          })
          .catch(function(error) {
            $scope.state = 'empty';
            $scope.privateBaseRepository = null;

            $scope.$apply(function() {
              opt_callback && opt_callback(false, error || 'Could not find valid Dockerfile');
            });
          });
      };

      $scope.handleFilesCleared = function() {
        $scope.state = 'empty';
        $scope.pullEntity = null;
        $scope.privateBaseRepository = null;
      };

      $scope.handleFilesValidated = function(uploadFiles) {
        $scope.uploadFilesCallback = uploadFiles;
      };

      var requestRepoBuild = function(buildPackId, opt_callback) {
        var repo = $scope.repository;
        var data = {
          'file_id': buildPackId
        };

        if ($scope.pullEntity) {
          data['pull_robot'] = $scope.pullEntity['name'];
        }

        var params = {
          'repository': repo.namespace + '/' + repo.name,
        };

        ApiService.requestRepoBuild(data, params).then(function(resp) {
          opt_callback && opt_callback(true, resp);
        }, function(resp) {
          opt_callback && opt_callback(false, 'Could not start build');
          $scope.handleFilesSelected($scope.selectedFiles);
        });
      };

      var startBuild = function(opt_callback) {
        $scope.state = 'uploading-files';
        $scope.uploadFilesCallback(function(status, messageOrIds) {
          $scope.state = 'starting-build';
          requestRepoBuild(messageOrIds[0], opt_callback);
        });
      };

      var checkEntity = function() {
        if (!$scope.pullEntity) {
          $scope.state = 'awaiting-bot';
          return;
        }

        $scope.state = 'checking-bot';
        $scope.currentRobotHasPermission = null;

        var permParams = {
          'repository': $scope.privateBaseRepository,
          'username': $scope.pullEntity.name
        };

        ApiService.getUserTransitivePermission(null, permParams).then(function(resp) {
          $scope.currentRobotHasPermission = resp['permissions'].length > 0;
          $scope.state = $scope.currentRobotHasPermission ? 'ready' : 'perm-error';
        });
      };

      $scope.$watch('pullEntity', checkEntity);
      $scope.$watch('reset', function(reset) {
        if (reset) {
          $scope.state = 'empty';
          $scope.pullEntity = null;
          $scope.privateBaseRepository = null;
        }
      });

      $scope.$watch('state', function(state) {
        $scope.isReady = state == 'ready';
        if ($scope.isReady) {
          $scope.readyForBuild({
            'startBuild': startBuild
          });
        }
      });
    }
  };
  return directiveDefinitionObject;
});