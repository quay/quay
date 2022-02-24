/**
 * Helper service for returning information extracted from repository image metadata.
 */
angular.module('quay').factory('ImageMetadataService', [function() {
  var metadataService = {};

  metadataService.getManifestCommand = function(manifest, blobDigest) {
    if (!manifest) {
      return null;
    }
    const layer = manifest.layers.find(layer => layer.blob_digest === blobDigest);

    return layer ? layer.command : null;
  }

  return metadataService;
}]);
