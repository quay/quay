/**
 * Directive to transclude a template under an ng-repeat. From: http://stackoverflow.com/a/24512435
 */
angular.module('quay').directive('ngTranscope', function() {
    return {
        link: function( $scope, $element, $attrs, controller, $transclude ) {
            if ( !$transclude ) {
                throw minErr( 'ngTranscope' )( 'orphan',
                    'Illegal use of ngTransclude directive in the template! ' +
                    'No parent directive that requires a transclusion found. ' +
                    'Element: {0}',
                    startingTag( $element ));
            }
            var innerScope = $scope.$new();

            $transclude( innerScope, function( clone ) {
                $element.empty();
                $element.append( clone );
                $element.on( '$destroy', function() {
                    innerScope.$destroy();
                });
            });
        }
    };
});
