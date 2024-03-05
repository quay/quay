/**
 * An element which displays a panel for managing users.
 */
angular.module('quay').directive('quotaManagementView', function () {
  var directiveDefinitionObject = {
    templateUrl: '/static/directives/quota-management-view.html',
    restrict: 'AEC',
    scope: {
      'view': '@view',
      'organization': '=organization',
      'user': '=user',
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
        'KiB': 1024,
        'MiB': 1024 ** 2,
        'GiB': 1024 ** 3,
        'TiB': 1024 ** 4,
      };
      $scope.quotaUnits = Object.keys($scope.disk_size_units);
      $scope.rejectLimitType = 'Reject';
      $scope.errorMessage = '';
      $scope.errorMessagesObj = {
        'quotaLessThanZero': 'A quota greater 0 must be defined.',
        'quotaLimitNotInRange': 'A quota limit greater 0 and less than 100 must be defined.',
        'validNumber': 'Please enter a valid number.',
        'setQuotaBeforeLimit': 'Please set quota before adding a quota Limit.',
        'singleRejectLimit': 'Error: A quota policy should only have a single reject threshold.',
        'identicalThresholds': 'Error: The quota policy contains two identical thresholds.',
        'decimalEntryError': 'Error: Decimal entries are not supported. Please enter a positive integer.',
      };
      $scope.warningMessage = '';
      $scope.warningMessagesObj = {
        'noQuotaLimit': 'Note: No quota policy defined. Users will be able to exceed the storage quota set above.',
        'noRejectLimit': 'Note: This quota has no hard limit enforced via a rejection thresholds. Users will be able to exceed the storage quota set above.',
        'usingDefaultQuota': 'Note: No quota policy defined for this organization, using system default.',
      }
      $scope.showConfigPanel = false;
      $scope.using_default_config = false;
      $scope.default_config_exists = false;
      $scope.quota_limit_error = false;

      let fetchSuperUSerNamespace = function () {
          if ($scope.organization != null) {
            return $scope.organization.name;
          }
          else {
            return $scope.user.username
          }
      }

      let fetchParams = function () {
        if ($scope.organization != null) {
            return {"orgname": $scope.organization.name};
          }
          else {
            return {"namespace": $scope.user.username};
          }
      }

      var loadOrgQuota = function () {
        if (!Features.QUOTA_MANAGEMENT || !Features.EDIT_QUOTA) {
          return;
        }

        let params = null;
        let method = null;
        if ($scope.organization != null){
          method = ApiService.listOrganizationQuota;
        } else {
          method = ApiService.listUserQuotaSuperUser;
        }
        params = fetchParams();

        $scope.nameSpaceResource = method(
          null, params
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
            $scope.using_default_config = quota["default_config"];
            $scope.default_config_exists = quota["default_config_exists"];
            $scope.warningMessage = "";

            if (quota["default_config"]) {
              $scope.warningMessage = $scope.warningMessagesObj["usingDefaultQuota"];
            }

            if (quota["limit_bytes"] != null) {
              $scope.prevquotaEnabled = true;
            }

            if ($scope.organization != null) {
              $scope.organization.quota_report.configured_quota = quota["limit_bytes"];
              $scope.organization.quota_report.percent_consumed = (parseInt($scope.organization.quota_report.quota_bytes) / $scope.organization.quota_report.configured_quota * 100).toFixed(2);
            }

          }
          populateDefaultQuotaLimits();
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
          result = Math.round(bytes / $scope.disk_size_units[byte_unit]);
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

          if ($scope.prevquotaEnabled && !$scope.using_default_config) {

            if ($scope.view == "super-user") {
              quotaMethod = ApiService.changeOrganizationQuotaSuperUser;
            } else {
              quotaMethod = ApiService.changeOrganizationQuota;
            }

          } else {

            if ($scope.view == "super-user") {
              quotaMethod = ApiService.createOrganizationQuotaSuperUser;
            } else {
              quotaMethod = ApiService.createNamespaceQuota;
            }

          }

          quotaMethod(data, params).then((resp) => {
            loadOrgQuota();
          }, function (resp) {
            handleError(resp)
          });
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
          'quota_id': $scope.currentQuotaConfig.id,
        };

        if ($scope.view == 'super-user') {
          params['namespace'] = fetchSuperUSerNamespace();
        } else {
          params['orgname'] = $scope.organization.name;
        }
        updateOrganizationQuota(params);
      }

      $scope.addQuotaLimit = function () {
        var params = {
          'orgname': fetchSuperUSerNamespace(),
          'quota_id': $scope.currentQuotaConfig.id,
        };

        var data = {
          'type': $scope.newLimitConfig['type'],
          'threshold_percent': $scope.newLimitConfig['limit_percent'],
        };

        ApiService.createOrganizationQuotaLimit(data, params).then((resp) => {
          if (!rejectLimitExists()) {
            $scope.newLimitConfig = {"limit_percent": 100, "type": $scope.rejectLimitType};
          } else {
            $scope.newLimitConfig['type'] = null;
            $scope.newLimitConfig['limit_percent'] = null;
          }
          loadOrgQuota();
        });
      }

      $scope.updateQuotaLimit = function (limitId) {
        var params = {
          'orgname': fetchSuperUSerNamespace(),
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
        }, function (resp) {
          handleError(resp);
        }
        );
      }

      $scope.deleteQuotaLimit = function (limitId) {
        const params = {
          'orgname': fetchSuperUSerNamespace(),
          'quota_id': $scope.currentQuotaConfig.id,
          'limit_id': limitId,
        }

        ApiService.deleteOrganizationQuotaLimit(null, params).then((resp) => {
          delete $scope.currentQuotaConfig['limits'][limitId];
          delete $scope.prevQuotaConfig['limits'][limitId];
          populateDefaultQuotaLimits();
        }, function (resp) {
          handleError(resp);
        });
      }

      let displayErrorAlert = function (message) {
        bootbox.alert(message);
      }

      let handleError = function (resp) {
        if (resp.status == 403) {
          displayErrorAlert("You do not have sufficient permissions to perform the action.");
        } else {
          displayErrorAlert(resp.data.error_message);
        }
      }

      $scope.disableSaveQuota = function () {
        // If quota exists and if user is in organization settings, cannot update the settings.
        if ($scope.prevquotaEnabled && $scope.view == "organization-view") {
          return true;
        }

        if (($scope.quota_limit_error && $scope.errorMessage != "") || !validOrgQuota()) {
          return true;
        }

        checkForWarnings();
        return $scope.prevQuotaConfig['quota'] === $scope.currentQuotaConfig['quota'] &&
          $scope.prevQuotaConfig['byte_unit'] === $scope.currentQuotaConfig['byte_unit'];
      }

      $scope.disableDeleteQuota = function () {
        // Cannot delete from organization settings page
        if ($scope.view == "organization-view") {
          return true;
        }
      }

      $scope.disableUpdateQuota = function (limitId) {
        // Cannot update from organization settings page
        if ($scope.view == "organization-view") {
          return true;
        }

        if (($scope.quota_limit_error && $scope.errorMessage != "") || !validOrgQuotaLimit($scope.currentQuotaConfig['limits'][limitId]['limit_percent'])) {
          return true;
        }
        return $scope.prevQuotaConfig['limits'][limitId]['type'] === $scope.currentQuotaConfig['limits'][limitId]['type'] &&
          $scope.prevQuotaConfig['limits'][limitId]['limit_percent'] === $scope.currentQuotaConfig['limits'][limitId]['limit_percent'];
      }

      var populateDefaultQuotaLimits = function () {
        if (Object.keys($scope.currentQuotaConfig['limits']).length > 0) {
          return;
        }
        $scope.newLimitConfig = {"limit_percent": 100, "type": $scope.rejectLimitType};
      }

      $scope.isObjectEmpty = function(obj){
        return Object.keys(obj).length === 0;
      }

      var multipleRejectTypes = function (obj) {
        let count = 0;
        for (var key in obj) {
          if (obj[key]['type'] == $scope.rejectLimitType) {
            count++;
          }
          if (count > 1) {
            return true;
          }
        }
        return false;
      }

      var isOfTypeDecimal = function (value) {
        if (value % 1 != 0) {
          $scope.errorMessage = $scope.errorMessagesObj['decimalEntryError'];
          return true;
        }
        return false;
      }

      $scope.disableAddQuotaLimit = function () {
        // Cannot add limits without configuring quota
        if (!$scope.currentQuotaConfig.id) {
          return true;
        }

        $scope.quota_limit_error = true;

        if ($scope.newLimitConfig['limit_percent'] != null && isNaN(parseInt($scope.newLimitConfig['limit_percent']))) {
          $scope.errorMessage = $scope.errorMessagesObj['quotaLimitNotInRange'];
          return true;
        }

        if (isOfTypeDecimal($scope.newLimitConfig['limit_percent'])) {
          return true;
        }

        let temp = {};
        temp['new'] = $scope.newLimitConfig;
        if (multipleRejectTypes({...$scope.prevQuotaConfig['limits'], ...temp})) {
          $scope.errorMessage = $scope.errorMessagesObj["singleRejectLimit"];
          return true;
        }

        // Check for duplicates in Quota Limit values
        if (duplicateExists($scope.currentQuotaConfig['limits'], $scope.newLimitConfig)) {
          $scope.errorMessage = $scope.errorMessagesObj["identicalThresholds"];
          updateErrorBorder(true);
          return true;
        }
        else {
          updateErrorBorder(false);
        }

        $scope.errorMessage = "";
        $scope.quota_limit_error = false;
        return false;
      }

      var validOrgQuotaLimit = function (limit_percent) {

        if (isNaN(parseInt(limit_percent))) {
          $scope.errorMessage = $scope.errorMessagesObj['quotaLimitNotInRange'];
          return false;
        }

        if (isOfTypeDecimal(limit_percent)) {
          return false;
        }

        $scope.errorMessage = '';
        return true;
      }

      var validOrgQuota = function () {
        // Empty state - when no quota is set. Don't throw any errors.
        if ($scope.currentQuotaConfig['quota'] == null && !$scope.prevquotaEnabled) {
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

        if (isOfTypeDecimal(parseFloat($scope.currentQuotaConfig['quota']))) {
          $scope.errorMessage = $scope.errorMessagesObj['decimalEntryError'];
          return false;
        }

        $scope.currentQuotaConfig['quota'] = parseInt($scope.currentQuotaConfig['quota']);
        $scope.errorMessage = '';

        // Enable Apply button only if quota and the unit is selected
        if (!$scope.currentQuotaConfig['quota'] || !$scope.currentQuotaConfig['byte_unit']) {
          return false;
        }
        return true;
      }

      var checkForWarnings = function() {
        // Do not over write existing warnings
        if ($scope.warningMessage) {
          return;
        }

        if (Object.keys($scope.currentQuotaConfig['limits']).length == 0) {
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

      $scope.deleteOrgQuota = function() {
        if ($scope.using_default_config) {
          bootbox.alert("The system default configuration cannot be removed.");
          return;
        }

        let alert_msg = '';
        if ($scope.default_config_exists) {
          alert_msg = 'When you remove the quota storage, users will use system\'s default quota.'
        } else {
          alert_msg = 'When you remove the quota storage, users can consume arbitrary amount of storage resources.'
        }

        bootbox.confirm('Are you sure you want to delete quota for this organization? ' + alert_msg,
        function(result) {
          if (!result) {
            return;loadOrgQuota
          }

          let handleSuccess = function() {
            loadOrgQuota();
            $scope.prevquotaEnabled = false;
            $scope.prevQuotaConfig = {'quota': null, 'limits': {}};
            $scope.currentQuotaConfig = {'quota': null, 'limits': {}};
            $scope.newLimitConfig = {'type': null, 'limit_percent': null};
          }

          let params =  {
            "quota_id": $scope.currentQuotaConfig.id
          }
          let quotaMethod = null;

          if ($scope.view == "super-user") {
            quotaMethod = ApiService.deleteOrganizationQuotaSuperUser;
            params["namespace"] = fetchSuperUSerNamespace();
          }
          else {
            quotaMethod = ApiService.deleteOrganizationQuota;
            params["orgname"] = $scope.organization.name;
          }

          quotaMethod(null, params).then((resp) => {
            handleSuccess();
          }, function(resp){
            handleError(resp);
          });
        });
      }


      var duplicateExists = function(obj, toCheck) {
        if (!obj || !toCheck) {
          return false;
        }

        for (let key in obj) {
          if (obj[key]['type'] === toCheck['type'] && obj[key]['limit_percent'] == toCheck['limit_percent']) {
            return true;
          }
        }
        return false;
      }

      var updateErrorBorder = function(toAdd) {
        var limitTypeEle = document.getElementById("newQuotaLimitType");
        var limitPercentEle = document.getElementById("newQuotaLimitPercent");

        if (toAdd) {
          limitTypeEle.classList.add("error-border");
          limitPercentEle.classList.add("error-border");
        }
        else {
          limitTypeEle.classList.remove("error-border");
          limitPercentEle.classList.remove("error-border");
        }
      }

      loadOrgQuota();
    }
  }
  return directiveDefinitionObject;
});
