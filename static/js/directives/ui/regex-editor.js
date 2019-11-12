/**
 * An element which displays an edit box for regular expressions.
 */
angular.module('quay').directive('regexEditor', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/regex-editor.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'placeholder': '@placeholder',
      'optional': '=optional',
      'binding': '=binding'
    },
    controller: function($scope, $element) {
    }
  };
  return directiveDefinitionObject;
});

angular.module('quay').directive('requireValidRegex', function() {
  return {
    require: 'ngModel',
    link: function(scope, element, attr, ctrl) {
      function validator(value) {
        try {
          new RegExp(value)
          ctrl.$setValidity('regex', true);
        } catch (e) {
          ctrl.$setValidity('regex', false);
        }
        return value;
      }

      ctrl.$parsers.push(validator);
    }
  };
});