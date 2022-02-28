/**
 * An element which displays a panel for managing users.
 */
angular.module('quay').directive('quotaManagementView', function () {
    var directiveDefinitionObject = {
        templateUrl: '/static/directives/quota-management-view.html',
        restrict: 'AEC',
        scope: {
            'organization': '=organization'
        },
        controller: function ($scope, $timeout, $location, $element, ApiService, UserService,
                          TableService, Features, StateService, $q) {
            $scope.prevquotaEnabled = false;
            $scope.updating = false;
            $scope.limitCounter = 0;
            $scope.quotaLimitTypes = [];
            $scope.quotaUnits = [];
            $scope.prevQuotaConfig = {'quota': null, 'limits': [], 'bytes_unit': null};
            $scope.currentQuotaConfig = {'quota': null, 'limits': [], 'bytes_unit': null};
            $scope.defer = null;

            var loadOrgQuota = function (fresh) {
                $scope.nameSpaceResource = ApiService.getNamespaceQuota(null,
                {'namespace': $scope.organization.name}).then((resp) => {
                    $scope.prevQuotaConfig['quota'] = resp["limit_bytes"];
                    $scope.currentQuotaConfig['quota'] = resp["limit_bytes"];
                    $scope.prevQuotaConfig['bytes_unit'] = resp["bytes_unit"];
                    $scope.currentQuotaConfig['bytes_unit'] = resp["bytes_unit"];
                    $scope.quotaUnits = resp["quota_units"];

                    if (fresh) {
                        for (let i = 0; i < resp["quota_limit_types"].length; i++) {
                            let temp = resp["quota_limit_types"][i];
                            temp["quota_limit_id"] = null;
                            $scope.quotaLimitTypes.push(temp);
                        }
                    }

                    if (resp["limit_bytes"] != null) {
                        $scope.prevquotaEnabled = true;
                    }
                });
            }

            var loadQuotaLimits = function (fresh) {
                $scope.nameSpaceQuotaLimitsResource = ApiService.getOrganizationQuotaLimit(null,
                    {'namespace': $scope.organization.name}).then((resp) => {
                    $scope.prevQuotaConfig['limits'] = [...resp['quota_limits']];
                    $scope.currentQuotaConfig['limits'] = [...resp['quota_limits']];

                    if (fresh) {
                      if ($scope.currentQuotaConfig['limits']) {
                        for (let i = 0; i < $scope.currentQuotaConfig['limits'].length; i++) {
                          populateQuotaLimit($scope.currentQuotaConfig['limits'][i]);
                        }
                      }
                    }
                });
            }

            var updateOrganizationQuota = function(data, params) {
                if (!$scope.prevquotaEnabled || $scope.prevQuotaConfig['quota'] != $scope.currentQuotaConfig['quota']) {
                    let quotaMethod = ApiService.createNamespaceQuota;
                    let m1 = "createNamespaceQuota";

                    if ($scope.prevquotaEnabled) {
                        quotaMethod = ApiService.changeOrganizationQuota;
                        m1 = "changeOrganizationQuota";
                    }

                    quotaMethod(data, params).then((resp) => {
                        $scope.updating = false;
                        $scope.prevQuotaConfig['quota'] = $scope.currentQuotaConfig['quota'];
                        $scope.prevQuotaConfig['bytes_unit'] = $scope.currentQuotaConfig['bytes_unit'];
                        $scope.prevquotaEnabled = true;
                    },  displayError());
                }
            }

            var createOrgQuotaLimit = function(data, params) {
                for (let i = 0; i < data.length; i++) {
                    let to_send = {
                        'percent_of_limit': data[i]['percent_of_limit'],
                        'quota_type_id': data[i]['limit_type']['quota_type_id']
                    };
                    ApiService.createOrganizationQuotaLimit(to_send, params).then((resp) => {
                        $scope.prevquotaEnabled = true;
                    }, displayError());
                }
            }

            var updateOrgQuotaLimit = function(data, params) {
                if (!data) {
                    return;
                }
                for (let i = 0; i < data.length; i++) {
                    let to_send = {
                        'percent_of_limit': data[i]['percent_of_limit'],
                        'quota_type_id': data[i]['limit_type']['quota_type_id'],
                        'quota_limit_id': data[i]['limit_type']['quota_limit_id']
                    };
                    ApiService.changeOrganizationQuotaLimit(to_send, params).then((resp) => {
                        $scope.prevquotaEnabled = true;
                    }, displayError());
                }
            }

            var deleteOrgQuotaLimit = function(data, params) {
                if (!data) {
                    return;
                }
                for (let i = 0; i < data.length; i++) {
                    params['quota_limit_id'] = data[i]['limit_type']['quota_limit_id'];
                    ApiService.deleteOrganizationQuotaLimit(null, params).then((resp) => {
                        $scope.prevquotaEnabled = true;
                    }, displayError());
                }
            }

            var similarLimits =function() {
                return JSON.stringify($scope.prevQuotaConfig['limits']) === JSON.stringify($scope.currentQuotaConfig['limits']);
            }

            var fetchLimitsToDelete = function() {
                // In prev but not in current => to be deleted
                let currentQuotaConfig = $scope.currentQuotaConfig['limits'];
                let prevQuotaConfig = $scope.prevQuotaConfig['limits'];
                return prevQuotaConfig.filter(function(obj1) {
                    return !currentQuotaConfig.some(function(obj2) {
                        return obj1.percent_of_limit === obj2.percent_of_limit && obj1.limit_type.name === obj2.limit_type.name;
                    });
                });
            }

            var fetchLimitsToAdd = function() {
                // In current but not in prev => to add
                let currentQuotaConfig = $scope.currentQuotaConfig['limits'];
                let prevQuotaConfig = $scope.prevQuotaConfig['limits'];
                return currentQuotaConfig.filter(function(obj1) {
                    return !prevQuotaConfig.some(function(obj2) {
                        return obj1.limit_type.name === obj2.limit_type.name && obj1.percent_of_limit === obj2.percent_of_limit;
                    });
                });
            }

            var fetchLimitsToUpdate = function() {
                // In current and prev but different values
                let currentQuotaConfig = $scope.currentQuotaConfig['limits'];
                let prevQuotaConfig = $scope.prevQuotaConfig['limits'];

                return currentQuotaConfig.filter(function(obj1) {
                    return prevQuotaConfig.some(function(obj2) {
                        return obj1.limit_type.quota_limit_id == obj2.limit_type.quota_limit_id &&
                            (obj1.percent_of_limit != obj2.percent_of_limit || obj1.limit_type.name != obj2.limit_type.name);
                    });
                });

            }

            var filterDelFromUpdateItems = function(deletedItems, updatedItems) {
                return updatedItems.filter(function(obj1) {
                    return !deletedItems.find(function(obj2) {
                        return obj1.limit_type.name === obj2.limit_type.name && obj1.percent_of_limit === obj2.percent_of_limit;
                    });
                });
            }

            var updateQuotaLimits = function(data, params) {
                if (similarLimits()) {
                    return;
                }

                let toDelete = fetchLimitsToDelete();
                let toAdd = fetchLimitsToAdd();
                let toUpdate = filterDelFromUpdateItems(toDelete, fetchLimitsToUpdate());

                createOrgQuotaLimit(toAdd, params);
                updateOrgQuotaLimit(toUpdate, params);
                deleteOrgQuotaLimit(toDelete, params);
            }

            var displayError = function(message = 'Could not update quota details') {
                $scope.updating = true;
                let errorDisplay = ApiService.errorDisplay(message, () => {
                    $scope.updating = false;
                });
                return errorDisplay;
            }

            var validLimits = function() {
                let valid = true;
                let rejectCount = 0;
                for (let i = 0; i < $scope.currentQuotaConfig['limits'].length; i++) {
                    if ($scope.currentQuotaConfig['limits'][i]['limit_type']['name'] === $scope.rejectLimitType) {
                        rejectCount++;

                        if (rejectCount > 1) {
                            let alert = displayError('You can only have one Reject type of Quota Limits. Please remove to proceed');
                            alert();
                            valid = false;
                            break;
                        }
                    }

                }
                return valid;
            }

            $scope.disableSave = function() {
                return $scope.prevQuotaConfig['quota'] === $scope.currentQuotaConfig['quota'] &&
                       $scope.prevQuotaConfig['bytes_unit'] === $scope.currentQuotaConfig['bytes_unit'] &&
                       similarLimits();
            }

            var updateQuotaDetails = function() {
                // If current state is same as previous do nothing
                if ($scope.disableSave()) {
                  return;
                }

                // Validate correctness
                if (!validLimits()) {
                  return;
                }

                let params = {
                  'namespace': $scope.organization.name
                };

                let data = {
                  'limit_bytes': $scope.currentQuotaConfig['quota'],
                  'bytes_unit': $scope.currentQuotaConfig['bytes_unit'],
                };

                updateOrganizationQuota(data, params);
                updateQuotaLimits(data, params);
                $scope.defer.resolve();
            }

            $scope.updateQuotaDetailsOnSave = function() {
                $scope.defer = $q.defer();
                updateQuotaDetails();
                 $scope.defer.promise.then(function() {
                    loadOrgQuota(false);
                    loadQuotaLimits(false);
                });
            }

            $scope.addQuotaLimit = function($event) {
                $scope.limitCounter++;
                let temp = {'percent_of_limit': '', 'limit_type': $scope.quotaLimitTypes[0]};
                $scope.currentQuotaConfig['limits'].push(temp);
                $event.preventDefault();
            }

            var populateQuotaLimit = function() {
                $scope.limitCounter++;
            }

            $scope.removeQuotaLimit = function(index) {
                $scope.currentQuotaConfig['limits'].splice(index, 1);
                $scope.limitCounter--;
            }

            loadOrgQuota(true);
            loadQuotaLimits(true);
        }
    }

    return directiveDefinitionObject;
});
