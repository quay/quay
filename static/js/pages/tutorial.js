(function() {
  /**
   * Interactive tutorial page.
   */
  angular.module('quayPages').config(['pages', function(pages) {
    pages.create('tutorial', 'tutorial.html', TutorialCtrl, {
      'newLayout': true,
      'title': 'Tutorial',
      'description': 'Basic tutorial on using Quay'
    })
  }]);

  function TutorialCtrl($scope, AngularTour, AngularTourSignals, UserService, Config, Features) {
    // Default to showing sudo on all commands if on linux.
    var showSudo = navigator.appVersion.indexOf("Linux") != -1;

    $scope.tour = {
      'title': Config.REGISTRY_TITLE_SHORT + ' Tutorial',
      'initialScope': {
        'showSudo': showSudo,
        'domainName': Config.getDomain()
      },
      'steps': [
        {
          'title': 'Welcome to the ' + Config.REGISTRY_TITLE_SHORT  + ' tutorial!',
          'templateUrl': '/static/tutorial/welcome.html'
        },
        {
          'title': 'Sign in to get started',
          'templateUrl': '/static/tutorial/signup.html',
          'signal': function($tourScope) {
            var user = UserService.currentUser();
            $tourScope.username = user.username;
            $tourScope.email = user.email;
            $tourScope.inOrganization = user.organizations && user.organizations.length > 0;
            return !user.anonymous;
          }
        },
        {
          'title': 'Step 1: Login to ' + Config.REGISTRY_TITLE_SHORT,
          'templateUrl': '/static/tutorial/docker-login.html',
          'signal': AngularTourSignals.serverEvent('/realtime/user/subscribe?events=docker-cli',
                                                   function(message) {
                                                     return message['data']['action'] == 'login';
                                                   }),
          'waitMessage': "Waiting for docker login",
          'skipTitle': "I'm already logged in",
          'mixpanelEvent': 'tutorial_start'
        },
        {
          'title': 'Step 2: Create a new container',
          'templateUrl': '/static/tutorial/create-container.html'
        },
        {
          'title': 'Step 3: Create a new image',
          'templateUrl': '/static/tutorial/create-image.html'
        },
        {
          'title': 'Step 4: Push the image to ' + Config.REGISTRY_TITLE_SHORT,
          'templateUrl': '/static/tutorial/push-image.html',
          'signal': AngularTourSignals.serverEvent('/realtime/user/subscribe?events=docker-cli',
                                                   function(message, tourScope) {
                                                     var pushing = message['data']['action'] == 'push_start';
                                                     if (pushing) {
                                                       tourScope.repoName = message['data']['repository'];
                                                     }
                                                     return pushing;
                                                   }),
          'waitMessage': "Waiting for repository push to begin",
          'mixpanelEvent': 'tutorial_wait_for_push'
        },
        {
          'title': 'Push in progress',
          'templateUrl': '/static/tutorial/pushing.html',
          'signal': AngularTourSignals.serverEvent('/realtime/user/subscribe?events=docker-cli',
                                                   function(message, tourScope) {
                                                     return message['data']['action'] == 'push_repo';
                                                   }),
          'waitMessage': "Waiting for repository push to complete"
        },
        {
          'title': 'Step 5: View the repository on ' + Config.REGISTRY_TITLE_SHORT,
          'templateUrl': '/static/tutorial/view-repo.html',
          'signal': AngularTourSignals.matchesLocation('/repository/'),
          'overlayable': true,
          'mixpanelEvent': 'tutorial_push_complete'
        },
        {
          'templateUrl': '/static/tutorial/view-repo.html',
          'signal': AngularTourSignals.matchesLocation('/repository/'),
          'overlayable': true
        },
        {
          'templateUrl': '/static/tutorial/waiting-repo-list.html',
          'signal': AngularTourSignals.elementAvaliable('*[data-repo="{{username}}/{{repoName}}"]'),
          'overlayable': true
        },
        {
          'templateUrl': '/static/tutorial/repo-list.html',
          'signal': AngularTourSignals.matchesLocation('/repository/{{username}}/{{repoName}}'),
          'element': '*[data-repo="{{username}}/{{repoName}}"]',
          'overlayable': true
        },
        {
          'title': 'Repository View',
          'content': 'This is the repository view page. It displays all the primary information about your repository',
          'overlayable': true,
          'mixpanelEvent': 'tutorial_view_repo'
        },
        {
          'title': 'Repository Tags',
          'content': 'Click on the tags tab to view all the tags in the repository',
          'overlayable': true,
          'element': '#tagsTab',
          'signal': AngularTourSignals.elementVisible('*[id="tagsTable"]')
        },
        {
          'title': 'Tag List',
          'content': 'The tag list displays shows the full list of active tags in the repository. ' +
            'You can click on an image to see its information or click on a tag to see its history.',
          'element': '#tagsTable',
          'overlayable': true
        },
        {
          'title': 'Tag Information',
          'content': 'Each row displays information about a specific tag',
          'element': '#tagsTable tr:first-child',
          'overlayable': true
        },
        {
          'title': 'Tag Actions',
          'content': 'You can modify a tag by clicking on the Tag Options icon',
          'element': '#tagsTable tr:first-child .fa-gear',
          'overlayable': true
        },
        {
          'title': 'Tag History',
          'content': 'You can view a tags history by clicking on the Tag History icon',
          'element': '#tagsTable tr:first-child .fa-history',
          'overlayable': true
        },
        {
          'title': 'Fetch Tag',
          'content': 'To see the various ways to fetch/pull a tag, click the Fetch Tag icon',
          'element': '#tagsTable tr:first-child .fa-download',
          'overlayable': true
        },
        {
          'content': 'To view the permissions for a repository, click on the Gear tab',
          'element': '#settingsTab',
          'overlayable': true,
          'signal': AngularTourSignals.elementVisible('*[id="repoPermissions"]')
        },
        {
          'title': 'Repository Settings',
          'content': "The repository settings tab allows for modification of a repository's permissions, notifications, visibility and other settings",
          'overlayable': true,
          'mixpanelEvent': 'tutorial_view_admin'
        },
        {
          'title': 'Permissions',
          'templateUrl': '/static/tutorial/permissions.html',
          'overlayable': true,
          'element': '#repoPermissions'
        },
        {
          'title': 'Adding a permission',
          'content': 'To add an <b>additional</b> permission, enter a username or robot account name into the autocomplete ' +
            'or hit the dropdown arrow to manage robot accounts',
          'overlayable': true,
          'element': '#add-entity-permission'
        },
        {
          'content': 'Repositories can be automatically populated in response to a Dockerfile build. To view the build settings for a repository, click on the builds tab',
          'element': '#buildsTab',
          'overlayable': true,
          'signal': AngularTourSignals.elementVisible('*[id="repoBuilds"]'),
          'skip': !Features.BUILD_SUPPORT
        },
        {
          'content': 'New build triggers can be created by clicking the "Create Build Trigger" button.',
          'element': '#addBuildTrigger',
          'overlayable': true,
          'skip': !Features.BUILD_SUPPORT
        },
        {
          'content': 'The full build history can always be referenced and filtered in the builds list.',
          'element': '#repoBuilds',
          'overlayable': true,
          'skip': !Features.BUILD_SUPPORT
        },
        {
          'templateUrl': '/static/tutorial/done.html',
          'overlayable': true,
          'mixpanelEvent': 'tutorial_complete'
        }
      ]
    };
  }
})();