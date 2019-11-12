/**
 * An element which displays a table of tokens on a repository and allows them to be
 * edited.
 */
angular.module('quay').directive('repositoryTokensTable', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/repository-tokens-table.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'repository': '=repository',
      'hasTokens': '=hasTokens',
      'isEnabled': '=isEnabled'
    },
    controller: function($scope, $element, ApiService, Restangular, UtilService) {
      $scope.hasTokens = false;

      var loadTokens = function() {
        if (!$scope.repository || $scope.tokensResource || !$scope.isEnabled) { return; }
        var params = {
          'repository': $scope.repository.namespace + '/' + $scope.repository.name
        };

        $scope.tokensResource = ApiService.listRepoTokensAsResource(params).get(function(resp) {
          $scope.tokens = resp.tokens;
          $scope.hasTokens = Object.keys($scope.tokens).length >= 1;
        }, ApiService.errorDisplay('Could not load access tokens'));
      };

      $scope.$watch('isEnabled', loadTokens);
      $scope.$watch('repository', loadTokens);

      loadTokens();

      $scope.deleteToken = function(tokenCode) {
        var params = {
          'repository': $scope.repository.namespace + '/' + $scope.repository.name,
          'code': tokenCode
        };

        ApiService.deleteToken(null, params).then(function() {
          delete $scope.tokens[tokenCode];
        });
      };

      $scope.changeTokenAccess = function(tokenCode, newAccess) {
        var role = {
          'role': newAccess
        };

        var params = {
          'repository': $scope.repository.namespace + '/' + $scope.repository.name,
          'code': tokenCode
        };

        ApiService.changeToken(role, params).then(function(updated) {
          $scope.tokens[updated.code] = updated;
        });
      };
    }
  };
  return directiveDefinitionObject;
});