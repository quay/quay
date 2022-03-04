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
            $scope.prevQuotaConfig = {'limit_bytes': null, 'quota': null, 'limits': [], 'bytes_unit': null};
            $scope.currentQuotaConfig = {'limit_bytes': null, 'quota': null, 'limits': [], 'bytes_unit': null};
            $scope.defer = null;
            $scope.disk_size_units = {
                'Bytes': 1,
                'KB': 1024**1,
                'MB': 1024**2,
                'GB': 1024**3,
                'TB': 1024**4,
            };
            $scope.quotaUnits = Object.keys($scope.disk_size_units);

            var loadOrgQuota = function (fresh) {
                $scope.nameSpaceResource = ApiService.getNamespaceQuota(null,
                {'namespace': $scope.organization.name}).then((resp) => {
                    $scope.prevQuotaConfig['limit_bytes'] = $scope.currentQuotaConfig['limit_bytes'] = resp["limit_bytes"];
                    let { result, byte_unit } = bytes_to_human_readable_string(resp["limit_bytes"]);
                    $scope.prevQuotaConfig['quota'] = $scope.currentQuotaConfig['quota'] = result
                    $scope.prevQuotaConfig['bytes_unit'] = $scope.currentQuotaConfig['bytes_unit'] = byte_unit;

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

            var human_readable_string_to_bytes = function(quota, bytes_unit) {
                if (bytes_unit == 'Bytes') {
                    return quota;
                }

                return Number(quota*$scope.disk_size_units[bytes_unit]);
            };

            var bytes_to_human_readable_string = function (bytes) {
                let units = Object.keys($scope.disk_size_units).reverse();
                let result = null;
                let byte_unit = null;
                for (const key in units) {
                    byte_unit = units[key];
                    if (bytes >= $scope.disk_size_units[byte_unit]) {
                        result = bytes / $scope.disk_size_units[byte_unit];
                        return { result, byte_unit };
                    }
                }
                return { result, byte_unit };
            };

            var loadQuotaLimits = function (fresh) {
                $scope.nameSpaceQuotaLimitsResource = ApiService.getOrganizationQuotaLimit(null,
                    {'namespace': $scope.organization.name}).then((resp) => {
                    $scope.prevQuotaConfig['limits'] = [];
                    $scope.currentQuotaConfig['limits'] = [];
                    for (let i = 0; i < resp['quota_limits'].length; i ++) {
                        $scope.prevQuotaConfig['limits'].push({...resp['quota_limits'][i]});
                        $scope.currentQuotaConfig['limits'].push({...resp['quota_limits'][i]});
                    }

                    if (fresh) {
                      if ($scope.currentQuotaConfig['limits']) {
                        for (let i = 0; i < $scope.currentQuotaConfig['limits'].length; i++) {
                          populateQuotaLimit();
                        }
                      }
                    }
                });
            }

            var updateOrganizationQuota = function(params) {

                if (!$scope.prevquotaEnabled || $scope.prevQuotaConfig['quota'] != $scope.currentQuotaConfig['quota']
                     || $scope.prevQuotaConfig['bytes_unit'] != $scope.currentQuotaConfig['bytes_unit'] ) {
                    let quotaMethod = ApiService.createNamespaceQuota;
                    let m1 = "createNamespaceQuota";
                    let limit_bytes = human_readable_string_to_bytes($scope.currentQuotaConfig['quota'], $scope.currentQuotaConfig['bytes_unit']);
                    let data = {
                        'limit_bytes': limit_bytes,
                    };

                    if ($scope.prevquotaEnabled) {
                        quotaMethod = ApiService.changeOrganizationQuota;
                        m1 = "changeOrganizationQuota";
                    }

                    quotaMethod(data, params).then((resp) => {
                        $scope.updating = false;
                        loadOrgQuota(false);
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
                    return obj1.limit_type.quota_limit_id != null && !currentQuotaConfig.some(function(obj2) {
                        return obj1.limit_type.quota_limit_id === obj2.limit_type.quota_limit_id;
                    });
                });
            }

            var fetchLimitsToAdd = function() {
                // In current but not in prev => to add
                let currentQuotaConfig = $scope.currentQuotaConfig['limits'];
                let prevQuotaConfig = $scope.prevQuotaConfig['limits'];
                return currentQuotaConfig.filter(function(obj1) {
                    return obj1.limit_type.quota_limit_id == null && !prevQuotaConfig.some(function(obj2) {
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

            var updateQuotaLimits = function(params) {
                if (similarLimits()) {
                    return;
                }

                let toDelete = fetchLimitsToDelete();
                let toAdd = fetchLimitsToAdd();
                let toUpdate = fetchLimitsToUpdate();

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

                updateOrganizationQuota(params);
                updateQuotaLimits(params);
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
