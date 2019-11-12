/**
 * An element which displays a dropdown select box which is (optionally) editable. This box
 * is displayed with an <input> and a menu on the right.
 */
angular.module('quay').directive('dropdownSelect', function ($compile) {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/dropdown-select.html',
    replace: true,
    transclude: true,
    restrict: 'C',
    scope: {
      'selectedItem': '=selectedItem',
      'placeholder': '=placeholder',
      'lookaheadItems': '=lookaheadItems',
      'hideDropdown': '=hideDropdown',

      'allowCustomInput': '@allowCustomInput',

      'handleItemSelected': '&handleItemSelected',
      'handleInput': '&handleInput',

      'clearValue': '=clearValue'
    },
    controller: function($scope, $element, $rootScope) {
      if (!$rootScope.__dropdownSelectCounter) {
        $rootScope.__dropdownSelectCounter = 1;
      }

      $scope.placeholder = $scope.placeholder || '';
      $scope.lookaheadSetup = false;

      // Setup lookahead.
      var input = $($element).find('.lookahead-input');

      $scope.$watch('clearValue', function(cv) {
        if (cv && $scope.lookaheadSetup) {
          $scope.selectedItem = null;
          $(input).typeahead('val', '');
          $(input).typeahead('close');
        }
      });

      $scope.$watch('selectedItem', function(item) {
        if (item != null && $scope.lookaheadSetup) {
          $(input).typeahead('val', item.toString());
          $(input).typeahead('close');
        }
      });

      $scope.$watch('lookaheadItems', function(items) {
        $(input).off();
        items = items || [];

        var formattedItems = [];
        for (var i = 0; i < items.length; ++i) {
          var formattedItem = items[i];
          if (typeof formattedItem == 'string') {
            formattedItem = {
              'value': formattedItem
            };
          }
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

        $(input).typeahead({
          'hint': false,
          'highlight': false
        }, {
          source: dropdownHound.ttAdapter(),
          templates: {
            'suggestion': function (datum) {
              template = datum['template'] ? datum['template'](datum) : '<span>' + datum['value'] + '</span>';
              return template;
            }
          }
        });

        $(input).on('input', function(e) {
          $scope.$apply(function() {
            $scope.selectedItem = null;
            if ($scope.handleInput) {
              $scope.handleInput({'input': $(input).val()});
            }
          });
        });

        $(input).on('typeahead:selected', function(e, datum) {
          $scope.$apply(function() {
            $scope.selectedItem = datum['item'] || datum['value'];
            if ($scope.handleItemSelected) {
              $scope.handleItemSelected({'datum': datum});
            }
          });
        });

        $rootScope.__dropdownSelectCounter++;
        $scope.lookaheadSetup = true;
      });
    },
    link: function(scope, element, attrs) {
      var transcludedBlock = element.find('div.transcluded');
      var transcludedElements = transcludedBlock.children();

      var iconContainer = element.find('div.dropdown-select-icon-transclude');
      var menuContainer = element.find('div.dropdown-select-menu-transclude');

      angular.forEach(transcludedElements, function(elem) {
        if (angular.element(elem).hasClass('dropdown-select-icon')) {
          iconContainer.append(elem);
        } else if (angular.element(elem).hasClass('dropdown-select-menu')) {
          menuContainer.replaceWith(elem);
        }
      });

      transcludedBlock.remove();
    }
  };
  return directiveDefinitionObject;
});


/**
 * An icon in the dropdown select. Only one icon will be displayed at a time.
 */
angular.module('quay').directive('dropdownSelectIcon', function () {
  var directiveDefinitionObject = {
    priority: 1,
    require: '^dropdownSelect',
    templateUrl: '/static/directives/dropdown-select-icon.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
    },
    controller: function($scope, $element) {
    }
  };
  return directiveDefinitionObject;
});


/**
 * The menu for the dropdown select.
 */
angular.module('quay').directive('dropdownSelectMenu', function () {
  var directiveDefinitionObject = {
    priority: 1,
    require: '^dropdownSelect',
    templateUrl: '/static/directives/dropdown-select-menu.html',
    replace: true,
    transclude: true,
    restrict: 'C',
    scope: {
    },
    controller: function($scope, $element) {
    }
  };
  return directiveDefinitionObject;
});
