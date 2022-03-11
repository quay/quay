/**
 * An element which displays a panel for managing users.
 */
angular.module('quay').directive('quotaManagementView', function () {
  var directiveDefinitionObject = {
    templateUrl: '/static/directives/quota-management-view.html',
    restrict: 'AEC',
    scope: {
      'isEnabled': '=isEnabled',
      'organization': '=organization',
    },
    controller: function ($scope, $timeout, $location, $element, ApiService, UserService,
                          TableService, Features, StateService, $q) {
      $scope.prevquotaEnabled = false;
      $scope.updating = false;
      $scope.limitCounter = 0;
      $scope.quotaLimitTypes = [
        "Reject", "Warning"
      ];

      $scope.prevQuotaConfig = {'quota': null, 'limits': {}};
      $scope.currentQuotaConfig = {'quota': null, 'limits': {}};
      $scope.newLimitConfig = {'type': null, 'limit_percent': null}

      $scope.defer = null;
      $scope.disk_size_units = {
	'KB': 1024,
        'MB': 1024**2,
        'GB': 1024**3,
        'TB': 1024**4,
      };
      $scope.quotaUnits = Object.keys($scope.disk_size_units);
      $scope.rejectLimitType = 'Reject';

      var loadOrgQuota = function () {
        $scope.nameSpaceResource = ApiService.listOrganizationQuota(
          null, {'orgname': $scope.organization.name}
        ).then((resp) => {
            if (resp.length > 0) {
              quota = resp[0];
              $scope.prevQuotaConfig['id'] = quota["id"];
	      $scope.currentQuotaConfig['id'] = quota["id"];
              
              for (i in quota['limits']) {
                limitId = quota['limits'][i]['id'];
                $scope.prevQuotaConfig['limits'][limitId] = $.extend({}, quota["limits"][i]);
		$scope.currentQuotaConfig['limits'][limitId] = $.extend({}, quota["limits"][i]);
              }

              let { result, byte_unit } = normalizeLimitBytes(quota["limit_bytes"]);
              $scope.prevQuotaConfig['quota'] = result;
	      $scope.currentQuotaConfig['quota'] = result;
              $scope.prevQuotaConfig['byte_unit'] = byte_unit;
	      $scope.currentQuotaConfig['byte_unit'] = byte_unit;

              if (quota["limit_bytes"] != null) {
                $scope.prevquotaEnabled = true;
              }

	      $scope.organization.quota_report.configured_quota = quota["limit_bytes"];
	      $scope.organization.quota_report.percent_consumed = (parseInt($scope.organization.quota_report.quota_bytes) / $scope.organization.quota_report.configured_quota * 100).toFixed(2);
            }
        });
      };

      var humanReadableStringToBytes = function(quota, bytes_unit) {
        return Number(quota*$scope.disk_size_units[bytes_unit]);
      };

      var normalizeLimitBytes = function (bytes) {
        let units = Object.keys($scope.disk_size_units).reverse();
        let result = null;
        let byte_unit = null;

        for (const key in units) {
          byte_unit = units[key];
          result = bytes / $scope.disk_size_units[byte_unit];
          if (bytes >= $scope.disk_size_units[byte_unit]) {
            return { result, byte_unit };
          }
        }
        
        return { result, byte_unit };
      };
      
      var updateOrganizationQuota = function(params) {
        let limit_bytes = humanReadableStringToBytes($scope.currentQuotaConfig['quota'], $scope.currentQuotaConfig['byte_unit']);
        let data = {'limit_bytes': limit_bytes};
        let quotaMethod = null;

        if (!$scope.prevquotaEnabled ||
            $scope.prevQuotaConfig['quota'] != $scope.currentQuotaConfig['quota'] ||
            $scope.prevQuotaConfig['byte_unit'] != $scope.currentQuotaConfig['byte_unit']) {
          if ($scope.prevquotaEnabled) {
            quotaMethod = ApiService.changeOrganizationQuota;
          } else {
            quotaMethod = ApiService.createOrganizationQuota;
          }
          quotaMethod(data, params).then((resp) => {
            loadOrgQuota();
          }, displayError());
        }
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
          if ($scope.currentQuotaConfig['limits'][i]['type'] === $scope.rejectLimitType) {
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
      
      $scope.updateQuotaConfig = function() {
        // Validate correctness
        if (!validLimits()) {
          $scope.defer.resolve();
          return;
        }
        
        let params = {
          'orgname': $scope.organization.name,
          'quota_id': $scope.currentQuotaConfig.id,
        };
        
        updateOrganizationQuota(params);
      }
      
      $scope.addQuotaLimit = function() {
	var params = {
          'orgname': $scope.organization.name,
          'quota_id': $scope.currentQuotaConfig.id,
	};

	var data = {
	  'type': $scope.newLimitConfig['type'],
	  'threshold_percent': $scope.newLimitConfig['limit_percent'],
	};

	ApiService.createOrganizationQuotaLimit(data, params).then((resp) => {
	  $scope.newLimitConfig['type'] = null;
	  $scope.newLimitConfig['limit_percent'] = null;
	  loadOrgQuota();
	});
      }

      $scope.updateQuotaLimit = function(limitId) {
	var params = {
          'orgname': $scope.organization.name,
          'quota_id': $scope.currentQuotaConfig.id,
          'limit_id': limitId,
	};

	var data = {
	  'type': $scope.currentQuotaConfig['limits'][limitId]['type'],
	  'threshold_percent': $scope.currentQuotaConfig['limits'][limitId]['limit_percent'],
	};

	ApiService.changeOrganizationQuotaLimit(data, params).then((resp) => {
	  $scope.prevQuotaConfig['limits'][limitId]['type'] = $scope.currentQuotaConfig['limits'][limitId]['type'];
	  $scope.prevQuotaConfig['limits'][limitId]['limit_percent'] = $scope.currentQuotaConfig['limits'][limitId]['limit_percent'];
	});
      }
      
      $scope.deleteQuotaLimit = function(limitId) {
        params = {
          'orgname': $scope.organization.name,
          'quota_id': $scope.currentQuotaConfig.id,
          'limit_id': limitId,
        }

        ApiService.deleteOrganizationQuotaLimit(null, params).then((resp) => {
          delete $scope.currentQuotaConfig['limits'][limitId];
	  delete $scope.prevQuotaConfig['limits'][limitId];
        });
      }

      $scope.disableSaveQuota = function() {
        return $scope.prevQuotaConfig['quota'] === $scope.currentQuotaConfig['quota'] &&
               $scope.prevQuotaConfig['byte_unit'] === $scope.currentQuotaConfig['byte_unit'];
      }

      $scope.disableUpdateQuota = function(limitId) {
        return $scope.prevQuotaConfig['limits'][limitId]['type'] === $scope.currentQuotaConfig['limits'][limitId]['type'] &&
	       $scope.prevQuotaConfig['limits'][limitId]['limit_percent'] === $scope.currentQuotaConfig['limits'][limitId]['limit_percent'];
      }      
      
      loadOrgQuota();
      /* loadQuotaLimits(true); */
      $scope.$watch('isEnabled', loadOrgQuota);
      $scope.$watch('organization', loadOrgQuota);
    }
  }
  
  return directiveDefinitionObject;
});
