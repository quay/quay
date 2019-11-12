/**
 * Helper service for retrieving the statuspage status of the quay service.
 */
angular.module('quay').factory('StatusService', ['Features', function(Features) {
  if (!Features.BILLING) {
    return {
      getStatus: function(callback) {}
    };
  }

  var STATUSPAGE_PAGE_ID = '8szqd6w4s277';
  var STATUSPAGE_SRC = 'https://statuspage-production.s3.amazonaws.com/se-v2.js';
  var statusPageHandler = null;
  var statusPageData = null;
  var callbacks = [];

  var handleGotData = function(data) {
    if (!data) { return; }
    statusPageData = data;

    for (var i = 0; i < callbacks.length; ++i) {
      callbacks[i](data);
    }

    callbacks = [];
  };

  $.getScript(STATUSPAGE_SRC, function(){
    statusPageHandler = new StatusPage.page({ page: STATUSPAGE_PAGE_ID });
    statusPageHandler.summary({
      success : handleGotData
    });
  });

  var statusService = {};
  statusService.getStatus = function(callback) {
    callbacks.push(callback);
    handleGotData(statusPageData);
  };

  return statusService;
}]);