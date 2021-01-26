/**
 * Service which defines the various kinds of external notification and provides methods for
 * easily looking up information about those kinds.
 */
angular.module('quay').factory('ExternalNotificationData', ['Config', 'Features','VulnerabilityService', 'DocumentationService',

function(Config, Features, VulnerabilityService, DocumentationService) {
  var externalNotificationData = {};

  var events = [
    {
      'id': 'repo_push',
      'title': 'Push to Repository',
      'icon': 'fa-upload'
    }
  ];

  if (Features.REPO_MIRROR) {
    var repoMirrorEvents = [
      {
        'id': 'repo_mirror_sync_started',
        'title': 'Repository Mirror Started',
        'icon': 'fa-circle-o-notch'
      },
      {
        'id': 'repo_mirror_sync_success',
        'title': 'Repository Mirror Success',
        'icon': 'fa-check-circle-o'
      },
      {
        'id': 'repo_mirror_sync_failed',
        'title': 'Repository Mirror Unsuccessful',
        'icon': 'fa-times-circle-o'
      }
    ];

    for (var i = 0; i < repoMirrorEvents.length; ++i) {
      events.push(repoMirrorEvents[i]);
    }
  }

  if (Features.BUILD_SUPPORT) {
    var buildEvents = [
      {
        'id': 'build_queued',
        'title': 'Dockerfile Build Queued',
        'icon': 'fa-tasks',
        'fields': [
          {
            'name': 'ref-regex',
            'type': 'regex',
            'title': 'matching ref(s)',
            'help_text': 'An optional regular expression for matching the git branch or tag ' +
                         'git ref. If left blank, the notification will fire for all builds.',
            'optional': true,
            'placeholder': '(refs/heads/somebranch)|(refs/tags/sometag)'
          }
        ]
      },
      {
        'id': 'build_start',
        'title': 'Dockerfile Build Started',
        'icon': 'fa-circle-o-notch',
        'fields': [
          {
            'name': 'ref-regex',
            'type': 'regex',
            'title': 'matching ref(s)',
            'help_text': 'An optional regular expression for matching the git branch or tag ' +
                         'git ref. If left blank, the notification will fire for all builds.',
            'optional': true,
            'placeholder': '(refs/heads/somebranch)|(refs/tags/sometag)'
          }
        ]
      },
      {
        'id': 'build_success',
        'title': 'Dockerfile Build Successfully Completed',
        'icon': 'fa-check-circle-o',
        'fields': [
          {
            'name': 'ref-regex',
            'type': 'regex',
            'title': 'matching ref(s)',
            'help_text': 'An optional regular expression for matching the git branch or tag ' +
                         'git ref. If left blank, the notification will fire for all builds.',
            'optional': true,
            'placeholder': '(refs/heads/somebranch)|(refs/tags/sometag)'
          }
        ]
      },
      {
        'id': 'build_failure',
        'title': 'Dockerfile Build Failed',
        'icon': 'fa-times-circle-o',
        'fields': [
          {
            'name': 'ref-regex',
            'type': 'regex',
            'title': 'matching ref(s)',
            'help_text': 'An optional regular expression for matching the git branch or tag ' +
                         'git ref. If left blank, the notification will fire for all builds.',
            'optional': true,
            'placeholder': '(refs/heads/somebranch)|(refs/tags/sometag)'
          }
        ]
      },
      {
        'id': 'build_cancelled',
        'title': 'Docker Build Cancelled',
        'icon': 'fa-minus-circle',
        'fields': [
          {
            'name': 'ref-regex',
            'type': 'regex',
            'title': 'matching ref(s)',
            'help_text': 'An optional regular expression for matching the git branch or tag ' +
                         'git ref. If left blank, the notification will fire for all builds.',
            'optional': true,
            'placeholder': '(refs/heads/somebranch)|(refs/tags/sometag)'
          }
        ]
      }];

    for (var i = 0; i < buildEvents.length; ++i) {
      events.push(buildEvents[i]);
    }
  }

  if (Features.SECURITY_SCANNER) {
    events.push({
      'id': 'vulnerability_found',
      'title': 'Package Vulnerability Found',
      'icon': 'fa-bug',
      'fields': [
        {
          'name': 'level',
          'type': 'enum',
          'title': 'minimum severity level',
          'values': VulnerabilityService.LEVELS,
          'help_text': 'A vulnerability must have a severity of the chosen level (or higher) ' +
                      'for this notification to fire.',
        }
      ]
    });
  }

  var methods = [
    {
      'id': 'quay_notification',
      'title': Config.REGISTRY_TITLE_SHORT + ' Notification',
      'icon': 'quay-icon',
      'fields': [
        {
          'name': 'target',
          'type': 'entity',
          'title': 'Recipient',
          'help_text': 'The ' + Config.REGISTRY_TITLE_SHORT + ' user to notify'
        }
      ]
    },
    {
      'id': 'email',
      'title': 'E-mail',
      'icon': 'fa-envelope',
      'fields': [
        {
          'name': 'email',
          'type': 'email',
          'title': 'E-mail address'
        }
      ],
      'enabled': Features.MAILING
    },
    {
      'id': 'webhook',
      'title': 'Webhook POST',
      'icon': 'fa-link',
      'fields': [
        {
          'name': 'url',
          'type': 'url',
          'title': 'Webhook URL',
          'help_text': 'JSON metadata representing the event will be POSTed to this URL.',
          'help_url': DocumentationService.getUrl('notifications')
        },
        {
          'name': 'template',
          'type': 'template',
          'title': 'POST body template (optional)',
          'help_text': 'If specified, a JSON template for formatting the body of the POST',
          'help_url':  DocumentationService.getUrl('notifications.webhook')
        }
      ]
    },
    {
      'id': 'flowdock',
      'title': 'Flowdock Team Notification',
      'icon': 'flowdock-icon',
      'fields': [
        {
          'name': 'flow_api_token',
          'type': 'string',
          'title': 'Flow API Token',
          'help_url': 'https://www.flowdock.com/account/tokens'
        }
      ]
    },
    {
      'id': 'hipchat',
      'title': 'HipChat Room Notification',
      'icon': 'hipchat-icon',
      'fields': [
        {
          'name': 'room_id',
          'type': 'pattern',
          'title': 'Room ID #',
          'pattern': '^[0-9]+$',
          'help_url': 'https://hipchat.com/admin/rooms',
          'pattern_fail_message': 'We require the HipChat room <b>number</b>, not name.'
        },
        {
          'name': 'notification_token',
          'type': 'string',
          'title': 'Room Notification Token',
          'help_url': 'https://hipchat.com/rooms/tokens/{room_id}'
        }
      ]
    },
    {
      'id': 'slack',
      'title': 'Slack Room Notification',
      'icon': 'slack-icon',
      'fields': [
        {
          'name': 'url',
          'type': 'pattern',
          'title': 'Webhook URL',
          'pattern': '^https://hooks\\.slack\\.com/services/[A-Z0-9]+/[A-Z0-9]+/[a-zA-Z0-9]+$',
          'help_url': 'https://slack.com/services/new/incoming-webhook',
          'placeholder': 'https://hooks.slack.com/service/{some}/{token}/{here}'
        }
      ]
    }
  ];

  var methodMap = {};
  var eventMap = {};

  for (var i = 0; i < methods.length; ++i) {
    methodMap[methods[i].id] = methods[i];
  }

  for (var i = 0; i < events.length; ++i) {
    eventMap[events[i].id] = events[i];
  }

  externalNotificationData.getSupportedEvents = function() {
    return events;
  };

  externalNotificationData.getSupportedMethods = function() {
    var filtered = [];
    for (var i = 0; i < methods.length; ++i) {
      if (methods[i].enabled !== false) {
        filtered.push(methods[i]);
      }
    }
    return filtered;
  };

  externalNotificationData.getEventInfo = function(event) {
    return eventMap[event];
  };

  externalNotificationData.getMethodInfo = function(method) {
    return methodMap[method];
  };

  return externalNotificationData;
}]);
