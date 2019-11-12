/**
 * An element which adds a stylize box for uploading a file.
 */
angular.module('quay').directive('fileUploadBox', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/file-upload-box.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'selectMessage': '@selectMessage',

      'filesSelected': '&filesSelected',
      'filesCleared': '&filesCleared',
      'filesValidated': '&filesValidated',

      'extensions': '<extensions',

      'reset': '=?reset'
    },
    controller: function($rootScope, $scope, $element, ApiService) {
      var MEGABYTE = 1000000;
      var MAX_FILE_SIZE = MAX_FILE_SIZE_MB * MEGABYTE;
      var MAX_FILE_SIZE_MB = 100;

      var number = $rootScope.__fileUploadBoxIdCounter || 0;
      $rootScope.__fileUploadBoxIdCounter = number + 1;

      $scope.boxId = number;
      $scope.state = 'clear';
      $scope.selectedFiles = [];

      var conductUpload = function(file, url, fileId, mimeType, progressCb, doneCb) {
        var request = new XMLHttpRequest();
        request.open('PUT', url, true);
        request.setRequestHeader('Content-Type', mimeType);
        request.onprogress = function(e) {
          $scope.$apply(function() {
            if (e.lengthComputable) { progressCb((e.loaded / e.total) * 100); }
          });
        };

        request.onerror = function() {
          $scope.$apply(function() { doneCb(false, 'Error when uploading'); });
        };

        request.onreadystatechange = function() {
          var state = request.readyState;
          var status = request.status;

          if (state == 4) {
            if (Math.floor(status / 100) == 2) {
              $scope.$apply(function() { doneCb(true, fileId); });
            } else {
              var message = request.statusText;
              if (status == 413) {
                message = 'Selected file too large to upload';
              }

              $scope.$apply(function() { doneCb(false, message); });
            }
          }
        };

        request.send(file);
      };

      var uploadFiles = function(callback) {
        var currentIndex = 0;
        var fileIds = [];

        var progressCb = function(progress) {
          $scope.uploadProgress = progress;
        };

        var doneCb = function(status, messageOrId) {
          if (status) {
            fileIds.push(messageOrId);
            currentIndex++;
            performFileUpload();
          } else {
            callback(false, messageOrId);
          }
        };

        var performFileUpload = function() {
          // If we have finished uploading all of the files, invoke the overall callback
          // with the list of file IDs.
          if (currentIndex >= $scope.selectedFiles.length) {
            callback(true, fileIds);
            return;
          }

          // For the current file, retrieve a file-drop URL from the API for the file.
          var currentFile = $scope.selectedFiles[currentIndex];
          var mimeType = currentFile.type || 'application/octet-stream';
          var data = {
            'mimeType': mimeType
          };

          $scope.currentlyUploadingFile = currentFile;
          $scope.uploadProgress = 0;

          ApiService.getFiledropUrl(data).then(function(resp) {
            // Perform the upload.
            conductUpload(currentFile, resp.url, resp.file_id, mimeType, progressCb, doneCb);
          }, function() {
            callback(false, 'Could not retrieve upload URL');
          });
        };

        // Start the uploading.
        $scope.state = 'uploading';
        performFileUpload();
      };

      $scope.handleFilesChanged = function(files) {
        if ($scope.state == 'uploading') { return; }

        $scope.message = null;
        $scope.selectedFiles = files;

        if (files.length == 0) {
          $scope.state = 'clear';
          $scope.filesCleared();
        } else {
          for (var i = 0; i < files.length; ++i) {
            if (files[i].size > MAX_FILE_SIZE) {
              $scope.state = 'error';
              $scope.message = 'File ' + files[i].name + ' is larger than the maximum file ' +
                               'size of ' + MAX_FILE_SIZE_MB + ' MB';
              return;
            }
          }

          $scope.state = 'checking';
          $scope.filesSelected({
            'files': files,
            'callback': function(status, message) {
              $scope.state = status ? 'okay' : 'error';
              $scope.message = message;

              if (status) {
                $scope.filesValidated({
                  'files': files,
                  'uploadFiles': uploadFiles
                });
              }
            }
          });
        }
      };

      $scope.getAccepts = function(extensions) {
        if (!extensions || !extensions.length) {
          return '*';
        }

        return extensions.join(',');
      };

      $scope.$watch('reset', function(reset) {
        if (reset) {
          $scope.state = 'clear';
          $element.find('#file-drop-' + $scope.boxId).parent().trigger('reset');
        }
      });
    }
  };
  return  directiveDefinitionObject;
});