const templateUrl = require('./file-upload-box.html');
/**
 * An element which adds a stylize box for uploading a file.
 */
angular.module('quay-config').directive('fileUploadBox', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl,
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'selectMessage': '@selectMessage',

      'filesSelected': '&filesSelected',
      'filesCleared': '&filesCleared',
      'filesValidated': '&filesValidated',

      'extensions': '<extensions',
      'apiEndpoint': '@apiEndpoint',

      'reset': '=?reset'
    },
    controller: function($rootScope, $scope, $element) {
      var MEGABYTE = 1000000;
      var MAX_FILE_SIZE = MAX_FILE_SIZE_MB * MEGABYTE;
      var MAX_FILE_SIZE_MB = 100;

      var number = $rootScope.__fileUploadBoxIdCounter || 0;
      $rootScope.__fileUploadBoxIdCounter = number + 1;

      $scope.boxId = number;
      $scope.state = 'clear';
      $scope.selectedFiles = [];

      var conductUpload = function(file, apiEndpoint, fileId, progressCb, doneCb) {
        var request = new XMLHttpRequest();
        request.open('PUT', '/api/v1/' + apiEndpoint, true);
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

        const formData = new FormData();
        formData.append('ca.crt', file);
        // FIXME(alecmerdler): Debugging
        console.log(formData);
        request.send(formData);
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

          $scope.currentlyUploadingFile = currentFile;
          $scope.uploadProgress = 0;

          conductUpload(currentFile, $scope.apiEndpoint, $scope.selectedFiles[0].name, progressCb, doneCb);
        };

        // Start the uploading.
        $scope.state = 'uploading';
        performFileUpload();
      };

      $scope.handleFilesChanged = function(files) {
        console.log(files);
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