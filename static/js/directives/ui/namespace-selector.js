/**
 * An element which displays a dropdown namespace selector or, if there is only a single namespace,
 * that namespace.
 */
angular.module('quay').directive('namespaceSelector', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/namespace-selector.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'user': '=user',
      'namespace': '=namespace',
      'requireCreate': '=requireCreate'
    },
    controller: function($scope, $element, $routeParams, $location, CookieService) {
      $scope.namespaces = {};

      $scope.initialize = function(user) {
        var preferredNamespace = user.username;
        var namespaces = {};
        namespaces[user.username] = user;
        if (user.organizations) {
          for (var i = 0; i < user.organizations.length; ++i) {
            namespaces[user.organizations[i].name] = user.organizations[i];
            if (user.organizations[i].preferred_namespace) {
              preferredNamespace = user.organizations[i].name;
            }
          }
        }

        var initialNamespace = $routeParams['namespace'] || CookieService.get('quay.namespace') ||
            preferredNamespace || $scope.user.username;
        $scope.namespaces = namespaces;
        $scope.setNamespace($scope.namespaces[initialNamespace]);
      };

      $scope.setNamespace = function(namespaceObj) {
        if (!namespaceObj) {
          namespaceObj = $scope.namespaces[$scope.user.username];
        }

        if ($scope.requireCreate && !namespaceObj.can_create_repo) {
          namespaceObj = $scope.namespaces[$scope.user.username];
        }

        var newNamespace = namespaceObj.name || namespaceObj.username;
        $scope.namespaceObj = namespaceObj;
        $scope.namespace = newNamespace;

        if (newNamespace) {
          CookieService.putPermanent('quay.namespace', newNamespace);

          if ($routeParams['namespace'] && $routeParams['namespace'] != newNamespace) {
            $location.search({'namespace': newNamespace});
          }
        }
      };

      $scope.$watch('namespace', function(namespace) {
        if ($scope.namespaceObj && namespace && namespace != $scope.namespaceObj.username) {
          $scope.setNamespace($scope.namespaces[namespace]);
        }
      });

      $scope.$watch('user', function(user) {
        $scope.user = user;
        $scope.initialize(user);
      });
    }
  };
  return directiveDefinitionObject;
});
