(function() {
  /**
   * Page to view the details of a single manifest.
   */
  angular.module('quayPages').config(['pages', function(pages) {
    pages.create('manifest-view', 'manifest-view.html', ManifestViewCtrl, {
      'newLayout': true,
      'title': '{{ manifest_digest }}',
      'description': 'Manifest {{ manifest_digest }}'
    })
  }]);

  function ManifestViewCtrl($scope, $routeParams, $rootScope, $timeout, ApiService, ImageMetadataService, Features, CookieService) {
    var namespace = $routeParams.namespace;
    var name = $routeParams.name;
    var manifest_digest = $routeParams.manifest_digest;

    $scope.manifestSecurityCounter = 0;
    $scope.manifestPackageCounter = 0;

    $scope.options = {
      'vulnFilter': ''
    };

    var loadManifest = function() {
      var params = {
        'repository': namespace + '/' + name,
        'manifestref': manifest_digest
      };

      $scope.manifestResource = ApiService.getRepoManifestAsResource(params).get(function(manifest) {
        $scope.manifest = manifest;
        $scope.reversedLayers = manifest.layers ? manifest.layers.reverse() : null;
      });
    };

    var loadRepository = function() {
      var params = {
        'repository': namespace + '/' + name,
        'includeTags': false
      };

      $scope.repositoryResource = ApiService.getRepoAsResource(params).get(function(repo) {
        $scope.repository = repo;
      });
    };

    loadManifest();
    loadRepository();

    $scope.loadManifestSecurity = function() {
      if (!Features.SECURITY_SCANNER) { return; }
      $scope.manifestSecurityCounter++;
    };

    $scope.loadManifestPackages = function() {
      if (!Features.SECURITY_SCANNER) { return; }
      $scope.manifestPackageCounter++;
    };

    $scope.manifestsOf = function(manifest) {
      if (!manifest || !manifest.is_manifest_list) {
        return [];
      }

      if (!manifest._mapped_manifests) {
        // Calculate once and cache to avoid angular digest cycles.
        var parsed_manifest = JSON.parse(manifest.manifest_data);

        manifest._mapped_manifests = parsed_manifest.manifests.map(function(manifest) {
          return {
            'repository': $scope.repository,
            'raw': manifest,
            'os': manifest.platform.os,
            'architecture': manifest.platform.architecture,
            'size': manifest.size,
            'digest': manifest.digest,
            'description': `${manifest.platform.os} on ${manifest.platform.architecture}`,
          };
        });
      }

      return manifest._mapped_manifests;
    };
  }
})();
