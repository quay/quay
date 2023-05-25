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
        controller: function ($scope, $timeout, $location, $element, ApiService) {
            $scope.prevEnabled = false;
            $scope.alertSaveSuccess = false;
            $scope.alertRemoveSuccess = false;

            $scope.initializeData = function () {
                return {
                    "org_name": $scope.organization.name,
                    "expiration_s": 86400,
                    "insecure": false,
                    'upstream_registry': null,
                    'upstream_registry_username': null,
                    'upstream_registry_password': null,
                };
            }
            $scope.currentConfig = $scope.initializeData();

            var fetchProxyConfig = function () {
                ApiService.getProxyCacheConfig(null, {'orgname': $scope.currentConfig.org_name})
                    .then((resp) => {
                        $scope.currentConfig['upstream_registry'] = resp["upstream_registry"];
                        $scope.currentConfig['expiration_s'] = resp["expiration_s"] || 86400;
                        $scope.currentConfig['insecure'] = resp["insecure"] || false;

                        if ($scope.currentConfig['upstream_registry']) {
                            $scope.prevEnabled = true;
                        }
                    });
            }

            var displayError = function (message = 'Could not update details') {
                let errorDisplay = ApiService.errorDisplay(message, () => {
                });
                return errorDisplay;
            }

            $scope.saveDetails = function () {
                let params = {'orgname': $scope.currentConfig.org_name};

                // validate payload
                ApiService.validateProxyCacheConfig($scope.currentConfig, params).then(function (response) {
                    if (response === "Valid" || response === "Anonymous") {
                        // save payload
                        ApiService.createProxyCacheConfig($scope.currentConfig, params).then((resp) => {
                            fetchProxyConfig();
                            alertSaveSuccessMessage();
                        }, displayError());
                    }
                }, displayError("Validation Error"));
            }

            var alertSaveSuccessMessage = function () {
                $timeout(function () {
                    $scope.alertSaveSuccess = true;
                }, 1);
                $timeout(function () {
                    $scope.alertSaveSuccess = false;
                }, 5000);
            };

            var alertRemoveSuccessMessage = function () {
                $timeout(function () {
                    $scope.alertRemoveSuccess = true;
                }, 1);
                $timeout(function () {
                    $scope.alertRemoveSuccess = false;
                }, 5000);
            };

            $scope.deleteConfig = function () {
                let params = {'orgname': $scope.currentConfig.org_name};
                ApiService.deleteProxyCacheConfig(null, params).then((resp) => {
                    $scope.prevEnabled = false;
                    alertRemoveSuccessMessage();
                }, displayError());
                $scope.currentConfig = $scope.initializeData();
            }

            fetchProxyConfig();
        }
    }

    return directiveDefinitionObject;
});
