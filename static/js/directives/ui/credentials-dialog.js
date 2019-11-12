/**
 * An element which displays a credentials dialog.
 */
angular.module('quay').directive('credentialsDialog', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/credentials-dialog.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'credentials': '=credentials',
      'secretTitle': '@secretTitle',
      'entityTitle': '@entityTitle',
      'entityIcon': '@entityIcon'
    },

    controller: function($scope, $element, $rootScope, Config) {
      $scope.Config = Config;

      $scope.k8s = {};
      $scope.rkt = {};
      $scope.docker = {};

      $scope.$on('$destroy', function() {
        if ($scope.inBody) {
          document.body.removeChild($element[0]);
        }
      });

      // Generate a unique ID for the dialog.
      if (!$rootScope.credentialsDialogCounter) {
        $rootScope.credentialsDialogCounter = 0;
      }

      $rootScope.credentialsDialogCounter++;

      $scope.hide = function() {
        $element.find('.modal').modal('hide');
      };

      $scope.show = function() {
        $element.find('.modal').modal({});

        // Move the dialog to the body to prevent it from being affected
        // by being placed inside other tables.
        $scope.inBody = true;
        document.body.appendChild($element[0]);
      };

      $scope.$watch('credentials', function(credentials) {
        if (!credentials) {
          $scope.hide();
          return;
        }

        $scope.show();
      });

      $scope.downloadFile = function(info) {
        var blob = new Blob([info.contents]);
        FileSaver.saveAs(blob, info.filename);
      };

      $scope.viewFile = function(context) {
        context.viewingFile = true;
      };

      $scope.isDownloadSupported = function() {
        var isSafari = /^((?!chrome).)*safari/i.test(navigator.userAgent);
        if (isSafari) {
          // Doesn't work properly in Safari, sadly.
          return false;
        }

        try { return !!new Blob(); } catch(e) {}
        return false;
      };

      $scope.getNamespace = function(credentials) {
        if (!credentials || !credentials.username) {
          return '';
        }

        if (credentials.namespace) {
          return credentials.namespace;
        }

        return credentials.username.split('+')[0];
      };

      $scope.getMesosFilename = function(credentials) {
        return $scope.getSuffixedFilename(credentials, 'auth.tar.gz');
      };

      $scope.getMesosFile = function(credentials) {
        var tarFile = new Tar();
        tarFile.append('.docker/config.json', $scope.getDockerConfig(credentials), {});
        contents = (new Zlib.Gzip(tarFile.getData())).compress();
        return {
          'filename': $scope.getMesosFilename(credentials),
          'contents': contents
        }
      };

      $scope.getDockerConfig = function(credentials) {
        var auths = {};
        auths[Config['SERVER_HOSTNAME']] = {
          'auth': $.base64.encode(credentials.username + ":" + credentials.password),
          'email': ''
        };

        var config = {
          'auths': auths
        };

        return JSON.stringify(config, null, '  ');
      };

      $scope.getDockerFile = function(credentials) {
        return {
          'filename': $scope.getRktFilename(credentials),
          'contents': $scope.getDockerConfig(credentials)
        }
      };

      $scope.getDockerLogin = function(credentials) {
        if (!credentials || !credentials.username) {
          return '';
        }

        var escape = function(v) {
          if (!v) { return v; }
          return v.replace('$', '\\$');
        };

        return 'docker login -u="' + escape(credentials.username) + '" -p="' + credentials.password + '" ' + Config['SERVER_HOSTNAME'];
      };

      $scope.getDockerFilename = function(credentials) {
        return $scope.getSuffixedFilename(credentials, 'auth.json')
      };

      $scope.getRktFile = function(credentials) {
        var config = {
          'rktKind': 'auth',
          'rktVersion': 'v1',
          'domains': [Config['SERVER_HOSTNAME']],
          'type': 'basic',
          'credentials': {
            'user': credentials['username'],
            'password': credentials['password']
          }
        };

        var contents = JSON.stringify(config, null, '  ');
        return {
          'filename': $scope.getRktFilename(credentials),
          'contents': contents
        }
      };

      $scope.getRktFilename = function(credentials) {
        return $scope.getSuffixedFilename(credentials, 'auth.json')
      };

      $scope.getKubernetesSecretName = function(credentials) {
        if (!credentials || !credentials.username) {
          return '';
        }

        return $scope.getSuffixedFilename(credentials, 'pull-secret');
      };

      $scope.getKubernetesFile = function(credentials) {
        var dockerConfigJson = $scope.getDockerConfig(credentials);
        var contents = 'apiVersion: v1\n' +
'kind: Secret\n' +
'metadata:\n' +
'  name: ' + $scope.getKubernetesSecretName(credentials) + '\n' +
'data:\n' +
'  .dockerconfigjson: ' + $.base64.encode(dockerConfigJson) + '\n' +
'type: kubernetes.io/dockerconfigjson'

        return {
          'filename': $scope.getKubernetesFilename(credentials),
          'contents': contents
        }
      };

      $scope.getKubernetesFilename = function(credentials) {
        return $scope.getSuffixedFilename(credentials, 'secret.yml')
      };

      $scope.getEscaped = function(item) {
        var escaped = item.replace(/[^a-zA-Z0-9]/g, '-');
        if (escaped[0] == '-') {
          escaped = escaped.substr(1);
        }
        return escaped;
      };

      $scope.getSuffixedFilename = function(credentials, suffix) {
        if (!credentials || !credentials.username) {
          return '';
        }

        var prefix = $scope.getEscaped(credentials.username);
        if (credentials.title) {
          prefix = $scope.getEscaped(credentials.title);
        }

        return prefix + '-' + suffix;
      };
    }
  };
  return directiveDefinitionObject;
});