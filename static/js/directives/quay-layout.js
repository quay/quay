/**
 * Directives which show, hide, include or otherwise mutate the DOM based on Features and Config.
 */


/**
 * Adds a quay-show attribute that shows the element only if the attribute evaluates to true.
 * The Features and Config services are added into the scope's context automatically.
 */
angular.module('quay').directive('quayShow', function($animate, Features, Config) {
  return {
    priority: 590,
    restrict: 'A',
    link: function($scope, $element, $attr, ctrl, $transclude) {
      $scope.Features = Features;
      $scope.Config = Config;
      $scope.$watch($attr.quayShow, function(result) {
        $animate[!!result ? 'removeClass' : 'addClass']($element, 'ng-hide');
      });
    }
  };
});


/**
 * Adds a quay-section attribute that adds an 'active' class to the element if the current URL
 * matches the given section.
 */
angular.module('quay').directive('quaySection', function($animate, $location, $rootScope) {
  return {
    priority: 590,
    restrict: 'A',
    link: function($scope, $element, $attr, ctrl, $transclude) {
      var update = function() {
        var result = $location.path().indexOf('/' + $attr.quaySection) == 0;
        $animate[!result ? 'removeClass' : 'addClass']($element, 'active');
      };

      $scope.$watch(function(){
        return $location.path();
      }, update);

      $scope.$watch($attr.quaySection, update);
    }
  };
});

/**
 * Adds a quay-classes attribute that performs like ng-class, but with Features and Config also
 * available in the scope automatically.
 */
angular.module('quay').directive('quayClasses', function(Features, Config) {
  return {
    priority: 580,
    restrict: 'A',
    link: function($scope, $element, $attr, ctrl, $transclude) {

      // Borrowed from ngClass.
      function flattenClasses(classVal) {
        if(angular.isArray(classVal)) {
          return classVal.join(' ');
        } else if (angular.isObject(classVal)) {
          var classes = [], i = 0;
          angular.forEach(classVal, function(v, k) {
            if (v) {
              classes.push(k);
            }
          });
          return classes.join(' ');
        }

        return classVal;
      }

      function removeClass(classVal) {
        $attr.$removeClass(flattenClasses(classVal));
      }


      function addClass(classVal) {
        $attr.$addClass(flattenClasses(classVal));
      }

      $scope.$watch($attr.quayClasses, function(result) {
        var scopeVals = {
          'Features': Features,
          'Config': Config
        };

        for (var expr in result) {
          if (!result.hasOwnProperty(expr)) { continue; }

          // Evaluate the expression with the entire features list added.
          var value = $scope.$eval(expr, scopeVals);
          if (value) {
            addClass(result[expr]);
          } else {
            removeClass(result[expr]);
          }
        }
      });
    }
  };
});

/**
 * Adds a quay-static-include attribute handles adding static marketing content from a defined
 * S3 bucket. If running under QE, the local template is used.
 *
 * Usage: quay-static-include="{'hosted': 'index.html', 'otherwise': 'partials/landing-login.html'}"
 */
angular.module('quay').directive('quayStaticInclude', function($compile, $templateCache, $http, Features, Config) {
  return {
    priority: 595,
    restrict: 'A',
    link: function($scope, $element, $attr, ctrl) {
      var getTemplate = function(hostedTemplateName, staticTemplateName) {
        var staticTemplateUrl = '/static/' + staticTemplateName;
        var templateUrl = staticTemplateUrl;
        if (Features.BILLING && Config['STATIC_SITE_BUCKET']) {
          templateUrl = Config['STATIC_SITE_BUCKET'] + hostedTemplateName;
        }

        return $http.get(templateUrl, {cache: $templateCache}).catch(function(resolve, reject) {
          // Fallback to the static local URL if the hosted URL doesn't work.
          return $http.get(staticTemplateUrl, {cache: $templateCache});
        });
      };

      var result = $scope.$eval($attr.quayStaticInclude);
      if (!result) {
        return;
      }

      var promise = getTemplate(result['hosted'], result['otherwise']).then(function (response) {
        $element.replaceWith($compile(response['data'])($scope));
        if ($attr.onload) {
          $scope.$eval($attr.onload);
        }
      }).catch(function(err) {
        console.log(err)
      });
    }
  };
});
