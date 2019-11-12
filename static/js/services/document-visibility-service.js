/**
 * Helper service which fires off events when the document's visibility changes, as well as allowing
 * other Angular code to query the state of the document's visibility directly.
 */
angular.module('quay').constant('CORE_EVENT', {
  DOC_VISIBILITY_CHANGE: 'core.event.doc_visibility_change'
});

angular.module('quay').factory('DocumentVisibilityService', ['$rootScope', '$document', 'CORE_EVENT',
    function($rootScope, $document, CORE_EVENT) {
  var document = $document[0],
  features,
  detectedFeature;

  function broadcastChangeEvent() {
    $rootScope.$broadcast(CORE_EVENT.DOC_VISIBILITY_CHANGE,
                          document[detectedFeature.propertyName]);
  }

  features = {
    standard: {
      eventName: 'visibilitychange',
      propertyName: 'hidden'
    },
    moz: {
      eventName: 'mozvisibilitychange',
      propertyName: 'mozHidden'
    },
    ms: {
      eventName: 'msvisibilitychange',
      propertyName: 'msHidden'
    },
    webkit: {
      eventName: 'webkitvisibilitychange',
      propertyName: 'webkitHidden'
    }
  };

  Object.keys(features).some(function(feature) {
    if (document[features[feature].propertyName] !== undefined) {
      detectedFeature = features[feature];
      return true;
    }
  });

  if (detectedFeature) {
    $document.on(detectedFeature.eventName, broadcastChangeEvent);
  }

  return {
    /**
     * Is the window currently hidden or not.
     */
    isHidden: function() {
      if (detectedFeature) {
        return document[detectedFeature.propertyName];
      }
    }
  };
}]);