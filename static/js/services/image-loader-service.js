/**
 * Helper service for tracking images needed by tags and caching them.
 */
angular.module('quay').factory('ImageLoaderService', ['ApiService', function(ApiService) {
  var imageLoader = function(namespace, name) {
    this.namespace = namespace;
    this.name = name;
    this.tagCache = {};
    this.images = [];
    this.imageMap = {};
    this.imageTagMap = {};
  };

  imageLoader.prototype.getTagSpecificImages = function(tag, callback) {
    var errorDisplay = ApiService.errorDisplay('Could not load tag specific images', function() {
      callback([]);
    });

    var params = {
      'repository': this.namespace + '/' + this.name,
      'tag': tag,
      'owned': true
    };

    ApiService.listTagImages(null, params).then(function(resp) {
      callback(resp['images']);
    }, errorDisplay);
  };

  imageLoader.prototype.getTagsForImage = function(image) {
    return this.imageTagMap[image.id] || [];
  };

  imageLoader.prototype.registerTagImages_ = function(tag, images) {
    this.tagCache[tag] = images;

    if (!images.length) {
      return;
    }

    var that = this;
    images.forEach(function(image) {
      if (!that.imageMap[image.id]) {
        that.imageMap[image.id] = image;
        that.images.push(image);
      }
    });

    var rootImage = images[0];
    if (!this.imageTagMap[rootImage.id]) {
      this.imageTagMap[rootImage.id] = [];
    }

    this.imageTagMap[rootImage.id].push(tag);
  }

  imageLoader.prototype.loadImages = function(tags, callback) {
    var toLoad = [];
    var that = this;
    tags.forEach(function(tag) {
      if (that.tagCache[tag]) {
        return;
      }

      toLoad.push(tag);
    });

    if (!toLoad.length) {
      callback();
      return;
    }

    var loadImages = function(index) {
      if (index >= toLoad.length) {
        callback();
        return;
      }

      var tag = toLoad[index];
      var params = {
        'repository': that.namespace + '/' + that.name,
        'tag': tag,
      };

      ApiService.listTagImages(null, params).then(function(resp) {
        that.registerTagImages_(tag, resp['images']);
        loadImages(index + 1);
      }, function() {
        loadImages(index + 1);
      })
    };

    loadImages(0);
  };

  imageLoader.prototype.reset = function() {
    this.tagCache = {};
    this.images = [];
    this.imageMap = {};
    this.imageTagMap = {};
  };

  var imageLoaderService = {};

  imageLoaderService.getLoader = function(namespace, name) {
    return new imageLoader(namespace, name);
  };

  return imageLoaderService
}]);