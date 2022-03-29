/**
 * An element which displays proxy cache configuration.
 */
angular.module('quay').directive('proxyCacheView', function () {
    var directiveDefinitionObject = {
        templateUrl: '/static/directives/proxy-cache-view.html',
        restrict: 'AEC',
        scope: {
            'organization': '=organization'
        },
        controller: function ($scope, $timeout, $location, $element, ApiService, UserService,
                          TableService, Features, StateService, $q) {
            $scope.prevEnabled = false;

            $scope.initializeData = function () {
                return {
                    'org_name': $scope.organization.name,
                    'upstream_registry': null,
                    'expiration_s': null,
                    'insecure': false,
                    'upstream_registry_username': null,
                    'upstream_registry_password': null,
                };
            }
            $scope.currentConfig = $scope.initializeData();

            var fetchProxyConfig = function () {
                ApiService.getProxyCacheConfig(null, {'orgname': $scope.currentConfig.org_name})
                    .then((resp) => {
                        $scope.currentConfig['upstream_registry'] = resp["upstream_registry"];
                        $scope.currentConfig['expiration_s'] = resp["expiration_s"];
                        $scope.currentConfig['insecure'] = resp["insecure"];

                        if ($scope.currentConfig['upstream_registry']) {
                            $scope.prevEnabled = true;
                        }
                    });
            }

            var displayError = function(message = 'Could not update details') {
                let errorDisplay = ApiService.errorDisplay(message, () => {});
                return errorDisplay;
            }

            $scope.saveDetails = function () {
                let params = {'orgname': $scope.currentConfig.org_name};
                ApiService.createProxyCacheConfig($scope.currentConfig, params).then((resp) => {
                    console.log("response is", resp);
                },  displayError());
                fetchProxyConfig();
            }

            $scope.deleteConfig = function () {
                let params = {'orgname': $scope.currentConfig.org_name};
                ApiService.deleteProxyCacheConfig(null, params).then((resp) => {
                    console.log("response is", resp);
                    $scope.prevEnabled = false;
                }, displayError());
                $scope.currentConfig = $scope.initializeData();
            }

            fetchProxyConfig();
        }
    }

    return directiveDefinitionObject;
});
