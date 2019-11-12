(function() {
  /**
   * Contact details page. The contacts are configurable.
   */
  angular.module('quayPages').config(['pages', function(pages) {
    pages.create('contact', 'contact.html', ContactCtrl, {
      'title': 'Contact Us'
    });
  }]);

  function ContactCtrl($scope, Config) {
    $scope.Config = Config;
    $scope.colsize = Math.floor(12 / Config.CONTACT_INFO.length);

    $scope.getKind = function(contactInfo) {
      var colon = contactInfo.indexOf(':');
      var scheme = contactInfo.substr(0, colon);
      if (scheme == 'https' || scheme == 'http') {
        if (contactInfo.indexOf('//twitter.com/') > 0) {
          return 'twitter';
        }

        return 'url';
      }

      return scheme;
    };

    $scope.getTitle = function(contactInfo) {
      switch ($scope.getKind(contactInfo)) {
        case 'url':
          return contactInfo;

        case 'twitter':
          var parts = contactInfo.split('/');
          return '@' + parts[parts.length - 1];

        case 'tel':
          return contactInfo.substr('tel:'.length);

        case 'irc':
          // irc://chat.freenode.net:6665/quayio
          var parts = contactInfo.substr('irc://'.length).split('/');
          var server = parts[0];
          if (server.indexOf('freenode') > 0) {
            server = 'Freenode';
          }
          return server + ': #' + parts[parts.length - 1];

        case 'mailto':
          return contactInfo.substr('mailto:'.length);
      }
    }
  }
})();