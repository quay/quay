/**
 * Helper service for returning information extracted from repository image metadata.
 */
angular.module('quay').factory('ImageMetadataService', [function() {
  var metadataService = {};

  metadataService.getImageCommand = function(image, imageId) {
    if (!image) {
      return null;
    }

    if (!image.__imageMap) {
      image.__imageMap = {};
      image.__imageMap[image.id] = image;

      for (var i = 0; i < image.history.length; ++i) {
        var cimage = image.history[i];
        image.__imageMap[cimage.id] = cimage;
      }
    }

    var found = image.__imageMap[imageId];
    if (!found) {
      return null;
    }

    return found.command;
  };

  metadataService.getManifestCommand = function(manifest, blobDigest) {
    if (!manifest) {
      return null;
    }
    const layer = manifest.layers.find(layer => layer.blob_digest === blobDigest);

    return layer ? layer.command : null;
  }

  return metadataService;
}]);