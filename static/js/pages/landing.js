(function() {
  /**
   * Landing page.
   */
  angular.module('quayPages').config(['pages', function(pages) {
    pages.create('landing', 'landing.html', LandingCtrl, {
      'pageClass': function(Features) {
        return Features.BILLING ? 'landing-page' : '';
      }
    });
  }]);

  function LandingCtrl($scope, $location, UserService, ApiService, Features, Config) {
    $scope.currentScreenshot = 'repo-view';
    $scope.userRegistered = false;

    if (!Config['SETUP_COMPLETE'] && !Features.BILLING) {
      $location.path('/incomplete-setup');
      return;
    }

    UserService.updateUserIn($scope, function(user) {
      if (!user.anonymous) {
        if (user.prompts && user.prompts.length) {
          $location.path('/updateuser/');
        } else {
          $location.path('/repository/');
        }
      }
    });

    $scope.handleUserRegistered = function() {
      $scope.userRegistered = true;
    };

    $scope.changeScreenshot = function(screenshot) {
      $scope.currentScreenshot = screenshot;
    };

    $scope.chromify = function() {
      browserchrome.update();

      var jcarousel = $('.jcarousel');

      jcarousel
        .on('jcarousel:reload jcarousel:create', function () {
          var width = jcarousel.innerWidth();
          jcarousel.jcarousel('items').css('width', width + 'px');
        })
        .jcarousel({
          wrap: 'circular'
        });

      $('.jcarousel-control-prev')
        .on('jcarouselcontrol:active', function() {
          $(this).removeClass('inactive');
        })
        .on('jcarouselcontrol:inactive', function() {
          $(this).addClass('inactive');
        })
        .jcarouselControl({
          target: '-=1'
        });

      $('.jcarousel-control-next')
        .on('jcarouselcontrol:active', function() {
          $(this).removeClass('inactive');
        })
        .on('jcarouselcontrol:inactive', function() {
          $(this).addClass('inactive');
        })
        .jcarouselControl({
          target: '+=1'
        });

      $('.jcarousel-pagination')
        .on('jcarouselpagination:active', 'a', function() {
          $(this).addClass('active');
        })
        .on('jcarouselpagination:inactive', 'a', function() {
          $(this).removeClass('active');
        })
        .jcarouselPagination({
          'item': function(page, carouselItems) {
            return '<a href="javascript:void(0)" class="jcarousel-page"></a>';
          }
        });
    };
  }
})();
