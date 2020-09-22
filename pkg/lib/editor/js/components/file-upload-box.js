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
      'certs': '=certs',
      'filesSelected': '&filesSelected',
      'filesCleared': '&filesCleared',
      'filesValidated': '&filesValidated',

      'extensions': '<extensions',

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
      $scope.selectedFiles = []

      $scope.handleFilesChanged = function(selectedFiles) {
        if ($scope.state == 'uploading') { return; }

        $scope.message = null;
        $scope.selectedFiles = selectedFiles
        if (selectedFiles.length == 0) {
          $scope.state = 'clear';
        } else {
          for (var i = 0; i < selectedFiles.length; ++i) {
            if (selectedFiles[i].size > MAX_FILE_SIZE) {
              $scope.state = 'error';
              $scope.message = 'File ' + selectedFiles[i].name + ' is larger than the maximum file ' +
                               'size of ' + MAX_FILE_SIZE_MB + ' MB';
              return;
            }
          }

          $scope.state = 'checking';
          $scope.filesSelected();

          for (var i = 0; i < selectedFiles.length; ++i) {
            conductUpload(selectedFiles[i])
          }
        }
      };


      var conductUpload = function(file) {
  
        var reader = new FileReader();
        reader.readAsText(file)
        
        reader.onprogress = function(e) {
          $scope.$apply(function() {
            if (e.lengthComputable) { 
              $scope.uploadProgress = (e.loaded / e.total) * 100
            }
          });
        }

        reader.onload = function(e){
          $scope.$apply(function(){
            $scope.certs["extra_ca_certs/"+file.name] = btoa(e.target.result)
            $scope.uploadProgress = 100
            $scope.state = 'okay'
          })
        }

        reader.onerror = function(e){
          $scope.$apply(function() { doneCb(false, 'Error when uploading'); });
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