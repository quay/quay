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
      $scope.newLimitConfig = {'type': null, 'limit_percent': null};

      $scope.defer = null;
      $scope.disk_size_units = {
        'KB': 1024,
        'MB': 1024 ** 2,
        'GB': 1024 ** 3,
        'TB': 1024 ** 4,
      };
      $scope.quotaUnits = Object.keys($scope.disk_size_units);
      $scope.rejectLimitType = 'Reject';
      $scope.errorMessage = '';
      $scope.errorMessagesObj = {
        'quotaLessThanZero': 'A quota greater 0 must be defined.',
        'quotaLimitNotInRange': 'A quota limit greater 0 and less than 100 must be defined.',
        'validNumber': 'Please enter a valid number.',
        'setQuotaBeforeLimit': 'Please set quota before adding a quota Limit.',
      };
      $scope.warningMessage = '';
      $scope.warningMessagesObj = {
        'noQuotaLimit': 'Note: No quota policy defined. Users will be able to exceed the storage quota set above.',
        'noRejectLimit': 'Note: This quota has no hard limit enforced via a rejection thresholds. Users will be able to exceed the storage quota set above.',
      }

      var loadOrgQuota = function () {
        $scope.nameSpaceResource = ApiService.listOrganizationQuota(
          null, {'orgname': $scope.organization.name}
        ).then((resp) => {
          if (resp.length > 0) {
            const quota = resp[0];
            $scope.prevQuotaConfig['id'] = quota["id"];
            $scope.currentQuotaConfig['id'] = quota["id"];

            for (const i in quota['limits']) {
              const limitId = quota['limits'][i]['id'];
              $scope.prevQuotaConfig['limits'][limitId] = $.extend({}, quota["limits"][i]);
              $scope.currentQuotaConfig['limits'][limitId] = $.extend({}, quota["limits"][i]);
            }

            let {result, byte_unit} = normalizeLimitBytes(quota["limit_bytes"]);
            $scope.prevQuotaConfig['quota'] = result;
            $scope.currentQuotaConfig['quota'] = result;
            $scope.prevQuotaConfig['byte_unit'] = byte_unit;
            $scope.currentQuotaConfig['byte_unit'] = byte_unit;

            if (quota["limit_bytes"] != null) {
              $scope.prevquotaEnabled = true;
            }

            $scope.organization.quota_report.configured_quota = quota["limit_bytes"];
            $scope.organization.quota_report.percent_consumed = (parseInt($scope.organization.quota_report.quota_bytes) / $scope.organization.quota_report.configured_quota * 100).toFixed(2);
          } else {
            populateDefaultQuotaLimits();
          }
        });
      };

      var humanReadableStringToBytes = function (quota, bytes_unit) {
        return Number(quota * $scope.disk_size_units[bytes_unit]);
      };

      var normalizeLimitBytes = function (bytes) {
        let units = Object.keys($scope.disk_size_units).reverse();
        let result = null;
        let byte_unit = null;

        for (const key in units) {
          byte_unit = units[key];
          result = bytes / $scope.disk_size_units[byte_unit];
          if (bytes >= $scope.disk_size_units[byte_unit]) {
            return {result, byte_unit};
          }
        }

        return {result, byte_unit};
      };

      var updateOrganizationQuota = function (params) {
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

      var displayError = function (message = 'Could not update quota details') {
        $scope.updating = true;
        let errorDisplay = ApiService.errorDisplay(message, () => {
          $scope.updating = false;
        });
        return errorDisplay;
      }

      var validLimits = function () {
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

      $scope.updateQuotaConfig = function () {
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

      $scope.addQuotaLimit = function () {
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

      $scope.updateQuotaLimit = function (limitId) {
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

      $scope.deleteQuotaLimit = function (limitId) {
        const params = {
          'orgname': $scope.organization.name,
          'quota_id': $scope.currentQuotaConfig.id,
          'limit_id': limitId,
        }

        ApiService.deleteOrganizationQuotaLimit(null, params).then((resp) => {
          delete $scope.currentQuotaConfig['limits'][limitId];
          delete $scope.prevQuotaConfig['limits'][limitId];
        });
      }

      $scope.disableSaveQuota = function () {
        if (!validOrgQuota()) {
          return true;
        }
        checkForWarnings();
        return $scope.prevQuotaConfig['quota'] === $scope.currentQuotaConfig['quota'] &&
          $scope.prevQuotaConfig['byte_unit'] === $scope.currentQuotaConfig['byte_unit'];
      }

      $scope.disableUpdateQuota = function (limitId) {
        if ($scope.errorMessage || !validOrgQuotaLimit($scope.currentQuotaConfig['limits'][limitId]['limit_percent'])) {
          return true;
        }
        return $scope.prevQuotaConfig['limits'][limitId]['type'] === $scope.currentQuotaConfig['limits'][limitId]['type'] &&
          $scope.prevQuotaConfig['limits'][limitId]['limit_percent'] === $scope.currentQuotaConfig['limits'][limitId]['limit_percent'];
      }

      var populateDefaultQuotaLimits = function () {
        if ($scope.prevquotaEnabled || $scope.currentQuotaConfig['limits'].length > 0) {
          return;
        }
        $scope.newLimitConfig = {"limit_percent": 100, "type": $scope.rejectLimitType};
      }

      $scope.disableAddQuotaLimit = function () {
        if (!$scope.currentQuotaConfig.id) {
          $scope.errorMessage = $scope.errorMessagesObj["setQuotaBeforeLimit"];
          return true;
        }

        $scope.errorMessage = "";
        return false;
      }

      var validOrgQuotaLimit = function (limit_percent) {
        if (isNaN(parseInt(limit_percent))) {
          $scope.errorMessage = $scope.errorMessagesObj['quotaLimitNotInRange'];
          return false;
        }

        $scope.errorMessage = '';
        return true;
      }

      var validOrgQuota = function () {
        // Empty state - when no quota is set. Don't throw any errors.
        if (!$scope.currentQuotaConfig['quota'] && !$scope.prevquotaEnabled) {
          $scope.errorMessage = '';
          return true;
        }

        if (isNaN(parseInt($scope.currentQuotaConfig['quota']))) {
          $scope.errorMessage = $scope.errorMessagesObj['validNumber'];
          return false;
        }

        if (parseInt($scope.currentQuotaConfig['quota']) <= 0) {
          $scope.errorMessage = $scope.errorMessagesObj['quotaLessThanZero'];
          return false;
        }

        $scope.errorMessage = '';
        return true;
      }

      var checkForWarnings = function() {
        if (Object.keys($scope.currentQuotaConfig['limits']).length == 0 && ($scope.newLimitConfig['type'] == null && $scope.newLimitConfig['limit_percent'] == null)) {
          $scope.warningMessage = $scope.warningMessagesObj['noQuotaLimit'];
          return;
        }

        if (!rejectLimitExists()) {
          $scope.warningMessage = $scope.warningMessagesObj['noRejectLimit'];
          return;
        }

        $scope.warningMessage = '';
      }

      var rejectLimitExists = function() {
        if ($scope.newLimitConfig['type'] == $scope.rejectLimitType) {
          return true;
        }

        for (var key in $scope.currentQuotaConfig['limits']) {
          if ($scope.currentQuotaConfig['limits'][key]['type'] == $scope.rejectLimitType) {
            return true;
          }
        }

        return false;
      }

      loadOrgQuota();
      /* loadQuotaLimits(true); */
      $scope.$watch('isEnabled', loadOrgQuota);
      $scope.$watch('organization', loadOrgQuota);
    }
  }
  return directiveDefinitionObject;
});
