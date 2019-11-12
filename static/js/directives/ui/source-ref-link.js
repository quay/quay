/**
 * An element which displays a link to a branch or tag in source control.
 */
angular.module('quay').directive('sourceRefLink', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/source-ref-link.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'ref': '=ref',
      'branchTemplate': '=branchTemplate',
      'tagTemplate': '=tagTemplate'
    },
    controller: function($scope, $element) {
      $scope.getKind = function(ref) {
        var parts = (ref || '').split('/');
        if (parts.length < 3) {
          return '';
        }

        return parts[1];
      };

      $scope.getTitle = function(ref) {
        var parts = (ref || '').split('/');
        if (parts.length < 3) {
          return '';
        }

        return parts.slice(2).join('/');
      };

      $scope.getUrl = function(ref, template, kind) {
        if (!template) { return ''; }
        return template.replace('{' + kind + '}', $scope.getTitle(ref));
      };
    }
  };
  return directiveDefinitionObject;
});
