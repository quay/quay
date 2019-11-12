/**
 * Service which defines the supported kinds of application notifications (those items that appear
 * in the sidebar) and provides helper methods for working with them.
 */
angular.module('quay').factory('NotificationService',
  ['$rootScope', '$interval', 'UserService', 'ApiService', 'StringBuilderService', 'PlanService', 'CookieService', 'Features', 'Config', '$location', 'VulnerabilityService', 'UtilService',

function($rootScope, $interval, UserService, ApiService, StringBuilderService, PlanService, CookieService, Features, Config, $location, VulnerabilityService, UtilService) {
  var notificationService = {
    'user': null,
    'notifications': [],
    'notificationClasses': [],
    'notificationSummaries': [],
    'expiringAppTokens': [],
    'additionalNotifications': false
  };

  var pollTimerHandle = null;

  var notificationKinds = {
    'test_notification': {
      'level': 'primary',
      'message': 'This notification is a long message for testing: {obj}',
      'page': '/about/',
      'dismissable': true
    },
    'org_team_invite': {
      'level': 'primary',
      'message': '{inviter} is inviting you to join team {team} under organization {org}',
      'actions': [
        {
          'title': 'Join team',
          'kind': 'primary',
          'handler': function(notification) {
            window.location = '/confirminvite?code=' + notification.metadata['code'];
          }
        },
        {
          'title': 'Decline',
          'kind': 'default',
          'handler': function(notification) {
            ApiService.declineOrganizationTeamInvite(null, {'code': notification.metadata['code']}).then(function() {
              notificationService.update();
            });
          }
        }
      ]
    },
    'password_required': {
      'level': 'error',
      'message': 'In order to begin pushing and pulling repositories, a password must be set for your account',
      'page': function(metadata) {
        return '/user/' + UserService.currentUser()['username'] + '?tab=settings';
      }
    },
    'over_private_usage': {
      'level': 'error',
      'message': 'Namespace {namespace} is over its allowed private repository count. ' +
        '<br><br>Please upgrade your plan to avoid disruptions in service.',
      'page': function(metadata) {
        var organization = UserService.getOrganization(metadata['namespace']);
        if (organization) {
          return '/organization/' + metadata['namespace'] + '?tab=billing';
        } else {
          return '/user/' + metadata['namespace'] + '?tab=billing';
        }
      }
    },
    'maintenance': {
      'level': 'warning',
      'message': 'We will be down for schedule maintenance from {from_date} to {to_date} ' +
        'for {reason}. We are sorry about any inconvenience.',
      'page': 'http://status.quay.io/'
    },
    'repo_push': {
      'level': 'info',
      'message': function(metadata) {
        if (metadata.updated_tags && Object.getOwnPropertyNames(metadata.updated_tags).length) {
          return 'Repository {repository} has been pushed with the following tags updated: {updated_tags}';
        } else {
          return 'Repository {repository} has been pushed';
        }
      },
      'page': function(metadata) {
        return '/repository/' + metadata.repository;
      },
      'dismissable': true
    },
    'repo_mirror_sync_started': {
      'level': 'info',
      'message': function(metadata) {
        if (metadata.message && Object.getOwnPropertyNames(metadata.message)) {
          return 'Repository Mirror started for {message}';
        } else {
          return 'Repository Mirror started for {repository}';
        }
      },
      'page': function(metadata) {
        return '/repository/' + metadata.repository;
      },
      'dismissable': true
    },
    'repo_mirror_sync_success': {
      'level': 'info',
      'message': function(metadata) {
        if (metadata.message && Object.getOwnPropertyNames(metadata.message)) {
          return 'Repository Mirror successful for {message}';
        } else {
          return 'Repository Mirror successful for {repository}';
        }
      },
      'page': function(metadata) {
        return '/repository/' + metadata.repository;
      },
      'dismissable': true
    },
    'repo_mirror_sync_failed': {
      'level': 'info',
      'message': function(metadata) {
        if (metadata.message && Object.getOwnPropertyNames(metadata.message)) {
          return 'Repository Mirror unsuccessful for {message}';
        } else {
          return 'Repository Mirror unsuccessful for {repository}';
        }
      },
      'page': function(metadata) {
        return '/repository/' + metadata.repository;
      },
      'dismissable': true
    },
    'build_queued': {
      'level': 'info',
      'message': 'A build has been queued for repository {repository}',
      'page': function(metadata) {
        return '/repository/' + metadata.repository + '/build/' + metadata.build_id;
      },
      'dismissable': true
    },
    'build_start': {
      'level': 'info',
      'message': 'A build has been started for repository {repository}',
      'page': function(metadata) {
        return '/repository/' + metadata.repository + '/build/' + metadata.build_id;
      },
      'dismissable': true
    },
    'build_success': {
      'level': 'info',
      'message': 'A build has succeeded for repository {repository}',
      'page': function(metadata) {
        return '/repository/' + metadata.repository + '/build/' + metadata.build_id;
      },
      'dismissable': true
    },
    'build_failure': {
      'level': 'error',
      'message': 'A build has failed for repository {repository}',
      'page': function(metadata) {
        return '/repository/' + metadata.repository + '/build/' + metadata.build_id;
      },
      'dismissable': true
    },
    'build_cancelled': {
      'level': 'info',
      'message': 'A build was cancelled for repository {repository}',
      'page': function(metadata) {
        return '/repository/' + metadata.repository + '/build/' + metadata.build_id;
      },
      'dismissable': true
    },
    'vulnerability_found': {
      'level': function(metadata) {
        var priority = metadata['vulnerability']['priority'];
        return VulnerabilityService.LEVELS[priority].level;
      },
      'message': 'A {vulnerability.priority} vulnerability was detected in repository {repository}',
      'page': function(metadata) {
        return '/repository/' + metadata.repository + '?tab=tags';
      },
      'dismissable': true
    },
    'service_key_submitted': {
      'level': 'primary',
      'message': 'Service key {kid} for service {service} requests approval<br><br>Key was created on {created_date}',
      'actions': [
        {
          'title': 'Approve Key',
          'kind': 'primary',
          'handler': function(notification) {
            var params = {
              'kid': notification.metadata.kid
            };

            ApiService.approveServiceKey({}, params).then(function(resp) {
              notificationService.update();
              window.location = '/superuser/?tab=servicekeys';
            }, ApiService.errorDisplay('Could not approve service key'));
          }
        },
        {
          'title': 'Delete Key',
          'kind': 'default',
          'handler': function(notification) {
            var params = {
              'kid': notification.metadata.kid
            };

            ApiService.deleteServiceKey(null, params).then(function(resp) {
              notificationService.update();
            }, ApiService.errorDisplay('Could not delete service key'));
          }
        }
      ],
      'page': function(metadata) {
        return '/superuser/?tab=servicekeys';
      },
    }
  };

  notificationService.dismissNotification = function(notification) {
    notification.dismissed = true;
    var params = {
      'uuid': notification.id
    };

    ApiService.updateUserNotification(notification, params).then(function(resp) {
      var index = $.inArray(notification, notificationService.notifications);
      if (index >= 0) {
        notificationService.notifications.splice(index, 1);
      }

      notificationService.update();
    }, ApiService.errorDisplay('Could not update notification'));
  };

  notificationService.getActions = function(notification) {
    var kindInfo = notificationKinds[notification['kind']];
    if (!kindInfo) {
      return [];
    }

    return kindInfo['actions'] || [];
  };

  notificationService.canDismiss = function(notification) {
    var kindInfo = notificationKinds[notification['kind']];
    if (!kindInfo) {
      return false;
    }
    return !!kindInfo['dismissable'];
  };

  notificationService.getPage = function(notification) {
    var kindInfo = notificationKinds[notification['kind']];
    if (!kindInfo) {
      return null;
    }

    var page = kindInfo['page'];
    if (page != null && typeof page != 'string') {
      page = page(notification['metadata']);
    }
    return page || '';
  };

  notificationService.getMessage = function(notification) {
    var kindInfo = notificationKinds[notification['kind']];
    if (!kindInfo) {
      return '(Unknown notification kind: ' + notification['kind'] + ')';
    }
    return StringBuilderService.buildTrustedString(kindInfo['message'], notification['metadata']);
  };

  notificationService.getBrowserNotificationMessage = function(notification) {
    var kindInfo = notificationKinds[notification['kind']];
    if (!kindInfo) {
      return '(Unknown notification kind: ' + notification['kind'] + ')';
    }

    const unsafeHtml = StringBuilderService.buildString(kindInfo['message'], notification['metadata']);
    return UtilService.removeHtmlTags(unsafeHtml);
  }

  notificationService.getClass = function(notification) {
    var kindInfo = notificationKinds[notification['kind']];
    if (!kindInfo) {
      return 'notification-info';
    }

    var level = kindInfo['level'];
    if (level != null && typeof level != 'string') {
      level = level(notification['metadata']);
    }

    return 'notification-' + level;
  };

  notificationService.getClasses = function(notifications) {
    if (!notifications.length) {
      return '';
    }

    var classes = [];
    for (var i = 0; i < notifications.length; ++i) {
      var notification = notifications[i];
      classes.push(notificationService.getClass(notification));
    }
    return classes.join(' ');
  };

  notificationService.update = function() {
    var user = UserService.currentUser();
    if (!user || user.anonymous) {
      return;
    }

    ApiService.listUserNotifications().then(function(resp) {
      notificationService.notifications = resp['notifications'];
      notificationService.additionalNotifications = resp['additional'];
      notificationService.notificationClasses = notificationService.getClasses(notificationService.notifications);

      if (notificationService.notifications.length > 0 && CookieService.get('quay.enabledDesktopNotifications') === 'on') {
        notificationService.sendBrowserNotifications();
      }
    });

    if (Features.APP_SPECIFIC_TOKENS) {
      var params = {
        'expiring': true
      };
      ApiService.listAppTokens(null, params).then(function(resp) {
        notificationService.expiringAppTokens = resp['tokens'];
      });
    }
  };

  notificationService.sendBrowserNotifications = () => {
    let mostRecentTimestamp = parseInt(CookieService.get('quay.notifications.mostRecentTimestamp'), 10);
    if (!mostRecentTimestamp) {
      mostRecentTimestamp = new Date(notificationService.notifications[0].created).getTime();
    }

    const newNotifications = notificationService.notifications
      .filter(obj => new Date(obj.created).getTime() > mostRecentTimestamp);

    if (newNotifications.length > 0) {
      let message = 'You have unread notifications';
      if (newNotifications.length === 1) {
        message = notificationService.getBrowserNotificationMessage(newNotifications[0]);
      }

      new Notification(message, {
        // Chrome doesn't display SVGs for notifications, so we'll use a default if we don't have an enterprise logo
        icon: window.location.origin + Config.getEnterpriseLogo('/static/img/quay-logo.png'),
        image: window.location.origin + Config.getEnterpriseLogo('/static/img/quay-logo.png'),
      });

      const newTimestamp = new Date(newNotifications[0].created).getTime();
      CookieService.putPermanent('quay.notifications.mostRecentTimestamp', newTimestamp.toString());
    }
  };

  notificationService.reset = function() {
    $interval.cancel(pollTimerHandle);
    pollTimerHandle = $interval(notificationService.update, 5 * 60 * 1000 /* five minutes */);
  };

  // Watch for plan changes and update.
  PlanService.registerListener(this, function(plan) {
    notificationService.reset();
    notificationService.update();
  });

  // Watch for user changes and update.
  $rootScope.$watch(function() { return UserService.currentUser(); }, function(currentUser) {
    notificationService.reset();
    notificationService.update();
  });

  return notificationService;
}]);
