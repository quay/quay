/**
 * An element which displays a dropdown select box which is (optionally) editable. This box
 * is displayed with an <input> and a menu on the right.
 */
angular.module('quay').directive('dropdownSelectDirect', function ($compile) {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/dropdown-select-direct.html',
    replace: true,
    transclude: true,
    restrict: 'C',
    scope: {
      'selectedItem': '=selectedItem',

      'placeholder': '=placeholder',
      'items': '=items',
      'iconMap': '=iconMap',

      'valueKey': '@valueKey',
      'titleKey': '@titleKey',
      'iconKey': '@iconKey',

      'noneIcon': '@noneIcon',

      'clearValue': '=clearValue'
    },
    controller: function($scope, $element, $rootScope) {
      if (!$rootScope.__dropdownSelectCounter) {
        $rootScope.__dropdownSelectCounter = 1;
      }

      $scope.placeholder = $scope.placeholder || '';
      $scope.internalItem = null;

      // Setup lookahead.
      var input = $($element).find('.lookahead-input');

      $scope.setItem = function(item) {
        $scope.selectedItem = item;
      };

      $scope.$watch('clearValue', function(cv) {
        if (cv) {
          $scope.selectedItem = null;
          $(input).val('');
        }
      });

      $scope.$watch('selectedItem', function(item) {
        if ($scope.selectedItem == $scope.internalItem) {
          // The item has already been set due to an internal action.
          return;
        }

        if ($scope.selectedItem != null) {
          $(input).val(item[$scope.valueKey]);
        } else {
          $(input).val('');
        }
      });

      $scope.$watch('items', function(items) {
        $(input).off();
        if (!items || !$scope.valueKey) {
          return;
        }

        var formattedItems = [];
        for (var i = 0; i < items.length; ++i) {
          var currentItem = items[i];
          var formattedItem = {
            'value': currentItem[$scope.valueKey],
            'item': currentItem
          };

          formattedItems.push(formattedItem);
        }

        var dropdownHound = new Bloodhound({
          name: 'dropdown-items-' + $rootScope.__dropdownSelectCounter,
          local: formattedItems,
          datumTokenizer: function(d) {
            return Bloodhound.tokenizers.whitespace(d.val || d.value || '');
          },
          queryTokenizer: Bloodhound.tokenizers.whitespace
        });
        dropdownHound.initialize();

        $(input).typeahead({}, {
          source: dropdownHound.ttAdapter(),
          templates: {
            'suggestion': function (datum) {
              template = datum['template'] ? datum['template'](datum) : datum['value'];
              return template;
            }
          }
        });

        $(input).on('input', function(e) {
          $scope.$apply(function() {
            $scope.internalItem = null;
            $scope.selectedItem = null;
          });
        });

        $(input).on('typeahead:selected', function(e, datum) {
          $scope.$apply(function() {
            $scope.internalItem = datum['item'];
            $scope.selectedItem = datum['item'];
          });
        });

        $rootScope.__dropdownSelectCounter++;
      });
    }
  };
  return directiveDefinitionObject;
});
