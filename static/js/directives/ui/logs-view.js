import { LogUsageChart } from '../../graphing';
import { parse } from 'path';
import { isNumber } from "util"
import moment from "moment"


/**
 * Element which displays usage logs for the given entity.
 */
angular.module('quay').directive('logsView', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/logs-view.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'organization': '=organization',
      'user': '=user',
      'makevisible': '=makevisible',
      'repository': '=repository',
      'allLogs': '@allLogs'
    },
    controller: function($scope, $element, $sce, Restangular, ApiService, TriggerService,
                         StringBuilderService, ExternalNotificationData, UtilService,
                         Features, humanizeIntervalFilter, humanizeDateFilter, StateService) {
      $scope.inReadOnlyMode = StateService.inReadOnlyMode();
      $scope.Features = Features;
      $scope.loading = true;
      $scope.loadCounter = -1;
      $scope.logs = null;
      $scope.kindsAllowed = null;
      $scope.chartVisible = true;
      $scope.chartLoading = true;

      $scope.options = {};
      $scope.context = {};

      var datetime = new Date();
      $scope.options.logStartDate = new Date(datetime.getUTCFullYear(), datetime.getUTCMonth(), datetime.getUTCDate() - 7);
      $scope.options.logEndDate = new Date(datetime.getUTCFullYear(), datetime.getUTCMonth(), datetime.getUTCDate());
      $scope.options.monthAgo = moment().subtract(1, 'month').calendar();
      $scope.options.now = new Date(datetime.getUTCFullYear(), datetime.getUTCMonth(), datetime.getUTCDate());

      var getOffsetDate = function(date, days) {
        return new Date(date.getFullYear(), date.getMonth(), date.getDate() + days);
      };

      var defaultPermSuffix = function(metadata) {
        if (metadata.activating_username) {
          return ', when creating user is {activating_username}';
        }
        return '';
      };

      var getServiceKeyTitle = function(metadata) {
        if (metadata.name) {
          return metadata.name;
        }

        return metadata.kind.substr(0, 12);
      };

      var logDescriptions = {
        'account_change_plan': 'Change plan',
        'account_change_cc': 'Update credit card',
        'account_change_password': 'Change password',
        'account_convert': 'Convert account to organization',
        'create_robot': 'Create Robot Account {robot}',
        'delete_robot': 'Delete Robot Account {robot}',
        'create_repo': 'Create Repository {namespace}/{repo}',
        'repo_mirror_sync_started': 'Mirror started for {message}',
        'repo_mirror_sync_success': 'Mirror finished successfully for {message}[[{tags}]]',
        'repo_mirror_sync_failed': 'Mirror finished unsuccessfully for {message}[[{tags}]][[ {stdout}]][[ {stderr}]]',
        'repo_mirror_sync_tag_success': 'Mirror of {tag} successful[[ to repository {namespace}/{repo}]][[ {message}]][[ {stdout}]][[ {stderr}]]',
        'repo_mirror_sync_tag_failed': 'Mirror of {tag} failure[[ to repository {namespace}/{repo}]][[ {message}]][[ {stdout}]][[ {stderr}]]',
        'repo_mirror_config_changed': function(metadata) {
          switch (metadata.changed) {
            case 'sync_status':
              if (metadata.to === 'SYNC_CANCEL') {
                return 'Mirror canceled';
              } else if (metadata.to === 'SYNC_NOW') {
                return 'Immediate mirror scheduled';
              } else {
                return 'Mirror {changed} changed to {to}';
              }
            case 'sync_start_date':
              metadata.changed = 'Sync Start Date';
              metadata.to = humanizeDateFilter(metadata.to);
              return 'Mirror {changed} changed to {to}';
            case 'sync_interval':
              metadata.changed = 'Sync Interval';
              metadata.to = humanizeIntervalFilter(metadata.to);
              return 'Mirror {changed} changed to {to}';
            case 'external_registry':
              metadata.changed = 'External Registry';
              return 'Mirror {changed} changed to {to}';
            case 'mirror_rule':
              metadata.changed = 'Tags';
              return 'Mirror {changed} changed to {to}';
            case 'external_registry':
              metadata.changed = 'External Registry';
              return 'Mirror {changed} changed to {to}';
            case 'is_enabled':
              metadata.changed = 'Enabled';
              return 'Mirror {changed} changed to {to}';
            case 'robot_username':
              metadata.changed = 'Robot User';
              return 'Mirror {changed} changed to {to}';
            case 'external_registry_username':
              metadata.changed = 'External Registry Username';
              return 'Mirror {changed} changed to {to}';
            case 'external_registry_password':
              metadata.changed = 'External Registry Password';
              return 'Mirror {changed} changed to {to}';
            case 'verify_tls':
              metadata.changed = 'Verify TLS';
              return 'Mirror {changed} changed to {to}';
            case 'http_proxy':
              metadata.changed = 'HTTP_PROXY';
              return 'Mirror {changed} changed to {to}';
            case 'https_proxy':
              metadata.changed = 'HTTPS_PROXY';
              return 'Mirror {changed} changed to {to}';
            case 'no_proxy':
              metadata.changed = 'NO_PROXY';
              return 'Mirror {changed} changed to {to}';
            default:
              return 'Mirror {changed} changed to {to}';
            }
        },
        'change_repo_state': 'Repository state changed to {state_changed}',
        'push_repo': function(metadata) {
          if (metadata.tag) {
            return 'Push of {tag}[[ to repository {namespace}/{repo}]]';
          } else if (metadata.release) {
            return 'Push of {release}[[ to repository {namespace}/{repo}]]';
          } else {
            return 'Repository push[[ to {namespace}/{repo}]]';
          }
        },
        'repo_verb': function(metadata) {
          var prefix = '';
          if (metadata.verb == 'squash') {
            prefix = 'Pull of squashed tag {tag}[[ from {namespace}/{repo}]]'
          } else if (metadata.verb == 'aci') {
            prefix = 'Pull of ACI of tag {tag}[[ from {namespace}/{repo}]]'
          } else {
            prefix = 'Pull of tag {tag}[[ from {namespace}/{repo}]]'
          }

          if (metadata.token) {
            if (metadata.token_type == 'build-worker') {
              prefix += '[[ by <b>build worker</b>]]';
            } else {
              prefix += '[[ via token]]';
            }
          } else if (metadata.username) {
            prefix += '[[ by {username}]]';
          } else {
            prefix += '[[ by {_ip}]]';
          }

          return prefix;
        },
        'pull_repo': function(metadata) {
          var description = 'repository {namespace}/{repo}';
          if (metadata.tag) {
            description = 'tag {tag}[[ from repository {namespace}/{repo}]]';
          } else if (metadata.manifest_digest) {
            description = 'digest {manifest_digest}[[ from repository {namespace}/{repo}]]';
          } else if (metadata.release) {
            description = 'release {release}';
            if (metadata.channel) {
              description += '[[ via channel {channel}]]';
            }
            if (metadata.mediatype) {
              description += '[[ for {mediatype}]]';
            }
            description += '[[ from repository {namespace}/{repo}]]';
          }

          if (metadata.token) {
            if (metadata.token_type == 'build-worker') {
              return 'Pull of ' + description + '[[ by <b>build worker</b>]]';
            } else {
              return 'Pull of ' + description + '[[ via token]]';
            }
            return prefix;
          } else if (metadata.username) {
            return 'Pull ' + description + '[[ by {username}]]';
          } else {
            return 'Public pull of ' + description + '[[ by {_ip}]]';
          }
        },
        'delete_repo': 'Delete repository {repo}',
        'change_repo_permission': function(metadata) {
          if (metadata.username) {
            return 'Change permission for [[user ]]{username}[[ in repository {namespace}/{repo}]] to {role}';
          } else if (metadata.team) {
              return 'Change permission for [[team ]]{team}[[ in repository {namespace}/{repo}]] to {role}';
          } else if (metadata.token) {
            return 'Change permission for [[token ]]{token}[[ in repository {namespace}/{repo}]] to {role}';
          }
        },
        'delete_repo_permission': function(metadata) {
          if (metadata.username) {
            return 'Remove permission for [[user ]]{username}[[ from repository {namespace}/{repo}]]';
          } else if (metadata.team) {
              return 'Remove permission for [[team ]]{team}[[ from repository {namespace}/{repo}]]';
          } else if (metadata.token) {
            return 'Remove permission for [[token ]]{token}[[ from repository {namespace}/{repo}]]';
          }
        },
        'revert_tag': function(metadata) {
          if (metadata.manifest_digest) {
            return 'Tag {tag} restored to {manifest_digest}';
          } else {
            return 'Tag {tag} restored to {image}';
          }
        },
        'delete_tag': 'Tag {tag} deleted[[ in repository {namespace}/{repo} by user {username}]]',
        'create_tag': 'Tag {tag} created[[ in repository {namespace}/{repo} on image {image} by user {username}]]',
        'move_tag': function(metadata) {
          if (metadata.manifest_digest) {
            return 'Tag {tag} moved[[ from {original_manifest_digest}]] to {manifest_digest}[[ in repository {namespace}/{repo} by user {username}]]';
          } else {
            return 'Tag {tag} moved[[ from image {original_image}]] to image {image}[[ in repository {namespace}/{repo} by user {username}]]';
          }
        },
        'change_repo_visibility': 'Change visibility[[ for repository {namespace}/{repo}]] to {visibility}',
        'change_repo_trust': function(metadata) {
          if (metadata.trust_enabled) {
            return 'Trust enabled[[ for {namespace}/{repo}]]';
          } else {
            return 'Trust disabled[[ for {namespace}/{repo}]]';
          }
        },
        'add_repo_accesstoken': 'Create access token {token}[[ in repository {repo}]]',
        'delete_repo_accesstoken': 'Delete access token {token}[[ in repository {repo}]]',
        'set_repo_description': 'Change description[[ for repository {namespace}/{repo} to {description}]]',
        'build_dockerfile': function(metadata) {
          if (metadata.trigger_id) {
            var triggerDescription = TriggerService.getDescription(
              metadata['service'], metadata['config']);
            return 'Build from Dockerfile[[ for repository {namespace}/{repo} triggered by ' + triggerDescription + ']]';
          }
          return 'Build from Dockerfile[[ for repository {namespace}/{repo}]]';
        },
        'org_create_team': 'Create team {team}',
        'org_delete_team': 'Delete team {team}',
        'org_add_team_member': 'Add member {member} to team {team}',
        'org_remove_team_member': 'Remove member {member} from team {team}',
        'org_invite_team_member': function(metadata) {
          if (metadata.user) {
            return 'Invite {user} to team {team}';
          } else {
            return 'Invite {email} to team {team}';
          }
        },
        'org_delete_team_member_invite': function(metadata) {
          if (metadata.user) {
            return 'Rescind invite of {user} to team {team}';
          } else {
            return 'Rescind invite of {email} to team {team}';
          }
        },

        'org_team_member_invite_accepted': 'User {member}, invited by {inviter}, joined team {team}',
        'org_team_member_invite_declined': 'User {member}, invited by {inviter}, declined to join team {team}',

        'org_set_team_description': 'Change description of team {team}[[ to {description}]]',
        'org_set_team_role': 'Change permission of team {team} to {role}',
        'create_prototype_permission': function(metadata) {
          if (metadata.delegate_user) {
            return 'Create default permission: {role} for {delegate_user}' + defaultPermSuffix(metadata);
          } else if (metadata.delegate_team) {
            return 'Create default permission: {role} for {delegate_team}' + defaultPermSuffix(metadata);
          }
        },
        'modify_prototype_permission': function(metadata) {
          if (metadata.delegate_user) {
            return 'Modify default permission: {role} (from {original_role}) for {delegate_user}' + defaultPermSuffix(metadata);
          } else if (metadata.delegate_team) {
            return 'Modify default permission: {role} (from {original_role}) for {delegate_team}' + defaultPermSuffix(metadata);
          }
        },
        'delete_prototype_permission': function(metadata) {
          if (metadata.delegate_user) {
            return 'Delete default permission: {role} for {delegate_user}' + defaultPermSuffix(metadata);
          } else if (metadata.delegate_team) {
            return 'Delete default permission: {role} for {delegate_team}' + defaultPermSuffix(metadata);
          }
        },
        'setup_repo_trigger': function(metadata) {
          var triggerDescription = TriggerService.getDescription(
            metadata['service'], metadata['config']);
          return 'Setup build trigger[[ - ' + triggerDescription + ']]';
        },
        'delete_repo_trigger': function(metadata) {
          var triggerDescription = TriggerService.getDescription(
            metadata['service'], metadata['config']);
          return 'Delete build trigger[[ - ' + triggerDescription + ']]';
        },
        'toggle_repo_trigger': function(metadata) {
          var triggerDescription = TriggerService.getDescription(
            metadata['service'], metadata['config']);
          if (metadata.enabled) {
            return 'Build trigger enabled[[ - ' + triggerDescription + ']]';
          } else {
            return 'Build trigger disabled[[ - ' + triggerDescription + ']]';
          }
        },
        'create_application': 'Create application {application_name}[[ with client ID {client_id}]]',
        'update_application': 'Update application to {application_name}[[ for client ID {client_id}]]',
        'delete_application': 'Delete application {application_name}[[ with client ID {client_id}]]',
        'reset_application_client_secret': 'Reset the client secret of application {application_name}[[ ' +
          'with client ID {client_id}]]',

        'add_repo_notification': function(metadata) {
          var eventData = ExternalNotificationData.getEventInfo(metadata.event);
          return 'Add notification of event "' + eventData['title'] + '"[[ for repository {namespace}/{repo}]]';
        },

        'delete_repo_notification': function(metadata) {
          var eventData = ExternalNotificationData.getEventInfo(metadata.event);
          return 'Delete notification of event "' + eventData['title'] + '"[[ for repository {namespace}/{repo}]]';
        },

        'reset_repo_notification': function(metadata) {
          var eventData = ExternalNotificationData.getEventInfo(metadata.event);
          return 'Re-enable notification of event "' + eventData['title'] + '"[[ for repository {namespace}/{repo}]]';
        },

        'regenerate_robot_token': 'Regenerated token for robot {robot}',

        'service_key_create': function(metadata) {
          if (metadata.preshared) {
            return 'Manual creation of[[ preshared service]] key {kid}[[ for service {service}]]';
          } else {
            return 'Creation of service key {kid} for service {service}[[ by {user_agent}]]';
          }
        },

        'service_key_approve': 'Approval of service key {kid}',
        'service_key_modify': 'Modification of service key {kid}',
        'service_key_delete': 'Deletion of service key {kid}',
        'service_key_extend': 'Change of expiration of service key {kid}[[ from {old_expiration_date}] to {expiration_date}',
        'service_key_rotate': 'Automatic rotation of service key {kid} by {user_agent}',

        'take_ownership': function(metadata) {
          if (metadata.was_user) {
            return '[Superuser ]{superuser} took ownership of user namespace {namespace}';
          } else {
            return '[Superuser ]{superuser} took ownership of organization {namespace}';
          }
        },

        'manifest_label_add': 'Label {key} added to[[ manifest]] {manifest_digest}[[ under repository {namespace}/{repo}]]',
        'manifest_label_delete': 'Label {key} deleted from[[ manifest]] {manifest_digest}[[ under repository {namespace}/{repo}]]',

        'change_tag_expiration': function(metadata) {
          if (metadata.expiration_date && metadata.old_expiration_date) {
            return 'Tag {tag} set to expire on {expiration_date}[[ (previously {old_expiration_date})]]';
          } else if (metadata.expiration_date) {
            return 'Tag {tag} set to expire on {expiration_date}';
          } else if (metadata.old_expiration_date) {
            return 'Tag {tag} set to no longer expire[[ (previously {old_expiration_date})]]';
          } else {
            return 'Tag {tag} set to no longer expire';
          }
        },

        'create_app_specific_token': 'Created external application token {app_specific_token_title}',
        'revoke_app_specific_token': 'Revoked external application token {app_specific_token_title}',
        'repo_mirror': function(metadata) {
          if (metadata.message) {
            return 'Repository mirror {verb} by Skopeo: {message}';
          } else {
            return 'Repository mirror {verb} by Skopeo';
          }
        },

        // Note: These are deprecated.
        'add_repo_webhook': 'Add webhook in repository {repo}',
        'delete_repo_webhook': 'Delete webhook in repository {repo}'
      };

      var logKinds = {
        'account_change_plan': 'Change plan',
        'account_change_cc': 'Update credit card',
        'account_change_password': 'Change password',
        'account_convert': 'Convert account to organization',
        'create_robot': 'Create Robot Account',
        'delete_robot': 'Delete Robot Account',
        'create_repo': 'Create Repository',
        'push_repo': 'Push to repository',
        'repo_verb': 'Pull Repo Verb',
        'pull_repo': 'Pull repository',
        'delete_repo': 'Delete repository',
        'change_repo_permission': 'Change repository permission',
        'delete_repo_permission': 'Remove user permission from repository',
        'change_repo_visibility': 'Change repository visibility',
        'change_repo_trust': 'Change repository trust settings',
        'add_repo_accesstoken': 'Create access token',
        'delete_repo_accesstoken': 'Delete access token',
        'set_repo_description': 'Change repository description',
        'build_dockerfile': 'Build image from Dockerfile',
        'delete_tag': 'Delete Tag',
        'create_tag': 'Create Tag',
        'move_tag': 'Move Tag',
        'revert_tag':'Restore Tag',
        'org_create_team': 'Create team',
        'org_delete_team': 'Delete team',
        'org_add_team_member': 'Add team member',
        'org_invite_team_member': 'Invite team member',
        'org_delete_team_member_invite': 'Rescind team member invitation',
        'org_remove_team_member': 'Remove team member',
        'org_team_member_invite_accepted': 'Team invite accepted',
        'org_team_member_invite_declined': 'Team invite declined',
        'org_set_team_description': 'Change team description',
        'org_set_team_role': 'Change team permission',
        'create_prototype_permission': 'Create default permission',
        'modify_prototype_permission': 'Modify default permission',
        'delete_prototype_permission': 'Delete default permission',
        'setup_repo_trigger': 'Setup build trigger',
        'delete_repo_trigger': 'Delete build trigger',
        'toggle_repo_trigger': 'Enable/disable build trigger',
        'create_application': 'Create Application',
        'update_application': 'Update Application',
        'delete_application': 'Delete Application',
        'reset_application_client_secret': 'Reset Client Secret',
        'add_repo_notification': 'Add repository notification',
        'delete_repo_notification': 'Delete repository notification',
        'reset_repo_notification': 'Re-enable repository notification',
        'regenerate_robot_token': 'Regenerate Robot Token',
        'service_key_create': 'Create Service Key',
        'service_key_approve': 'Approve Service Key',
        'service_key_modify': 'Modify Service Key',
        'service_key_delete': 'Delete Service Key',
        'service_key_extend': 'Extend Service Key Expiration',
        'service_key_rotate': 'Automatic rotation of Service Key',
        'take_ownership': 'Take Namespace Ownership',
        'manifest_label_add': 'Add Manifest Label',
        'manifest_label_delete': 'Delete Manifest Label',
        'change_tag_expiration': 'Change tag expiration',
        'create_app_specific_token': 'Create external app token',
        'revoke_app_specific_token': 'Revoke external app token',
        'repo_mirror_enabled': 'Enable Repository Mirror',
        'repo_mirror_disabled': 'Disable Repository Mirror',
        'repo_mirror_config_changed': 'Changed Repository Mirror',
        'repo_mirror_sync_started': 'Started Repository Mirror',
        'repo_mirror_sync_failed': 'Repository Mirror sync failed',
        'repo_mirror_sync_success': 'Repository Mirror sync success',
        'repo_mirror_sync_now_requested': 'Repository Mirror immediate sync requested',
        'repo_mirror_sync_tag_success': 'Repository Mirror tag sync successful',
        'repo_mirror_sync_tag_failed': 'Repository Mirror tag sync failed',
        'repo_mirror_sync_test_success': 'Test Repository Mirror success',
        'repo_mirror_sync_test_failed': 'Test Repository Mirror failed',
        'repo_mirror_sync_test_started': 'Test Repository Mirror started',
        
        // Note: these are deprecated.
        'add_repo_webhook': 'Add webhook',
        'delete_repo_webhook': 'Delete webhook'
      };

      var getDateString = function(date) {
        return (date.getMonth() + 1) + '/' + date.getDate() + '/' + date.getFullYear();
      };

      var getUrl = function(suffix) {
        var url = UtilService.getRestUrl('user/' + suffix);
        if ($scope.organization) {
          url = UtilService.getRestUrl('organization', $scope.organization.name, suffix);
        }
        if ($scope.repository) {
          url = UtilService.getRestUrl('repository', $scope.repository.namespace, $scope.repository.name, suffix);
        }

        if ($scope.allLogs) {
          url = UtilService.getRestUrl('superuser', suffix)
        }

        url.setQueryParameter('starttime', getDateString($scope.options.logStartDate));
        url.setQueryParameter('endtime', getDateString($scope.options.logEndDate));
        return url;
      };

      var update = function() {
        var hasValidUser = !!$scope.user;
        var hasValidOrg = !!$scope.organization;
        var hasValidRepo = $scope.repository && $scope.repository.namespace;
        var isValidEndpoint = hasValidUser || hasValidOrg || hasValidRepo || $scope.allLogs;

        var hasValidLogStartDate = !!$scope.options.logStartDate;
        var hasValidLogEndDate = !!$scope.options.logEndDate;

        var isValid = isValidEndpoint && hasValidLogStartDate && hasValidLogEndDate;

        if (!$scope.makevisible || !isValid || ($scope.loading && $scope.loadCounter >= 0)) {
          return;
        }

        if (Features.AGGREGATED_LOG_COUNT_RETRIEVAL) {
          $scope.chartLoading = true;

          var aggregateUrl = getUrl('aggregatelogs').toString();
          var loadAggregate = Restangular.one(aggregateUrl);
          loadAggregate.customGET().then(function(resp) {
            $scope.chart = new LogUsageChart(logKinds);
            $($scope.chart).bind('filteringChanged', function(e) {
              $scope.$apply(function() { $scope.kindsAllowed = e.allowed; });
            });

            $scope.chart.draw('bar-chart', resp.aggregated, $scope.options.logStartDate,
                              $scope.options.logEndDate);
            $scope.chartLoading = false;
          });
        }

        $scope.nextPageToken = null;
        $scope.hasAdditional = true;
        $scope.loading = false;
        $scope.logs = [];
        $scope.nextPage();
      };

      $scope.nextPage = function() {
        if ($scope.loading || !$scope.hasAdditional) { return; }

        $scope.loading = true;
        $scope.loadCounter++;

        var currentCounter = $scope.loadCounter;
        var url = getUrl('logs');
        url.setQueryParameter('next_page', $scope.nextPageToken);

        var loadLogs = Restangular.one(url.toString());
        loadLogs.customGET().then(function(resp) {
          if ($scope.loadCounter != currentCounter) {
            // Loaded logs data is out of date.
            return;
          }

          // Query next logentry tables when no logs are returned BUT a page token is.
          if (resp.logs === undefined || resp.logs.length == 0 && !!resp.next_page) {
            $scope.loading = false;
            $scope.nextPageToken = resp.next_page;
            $scope.hasAdditional = !!resp.next_page;
            $scope.nextPage();
          }

          resp.logs.forEach(function(log) {
            $scope.logs.push(log);
          });

          $scope.loading = false;
          $scope.nextPageToken = resp.next_page;
          $scope.hasAdditional = !!resp.next_page;
        });
      };

      $scope.toggleChart = function() {
        $scope.chartVisible = !$scope.chartVisible;
      };

      $scope.isVisible = function(allowed, kind) {
        return allowed == null || allowed.hasOwnProperty(kind);
      };

      $scope.toggleExpanded = function(log) {
        log._expanded = !log._expanded;
      };

      $scope.getColor = function(kind, chart) {
        if (!chart) { return 'gray'; }
        return chart.getColor(kind);
      };

      $scope.getDescription = function(log, full_description) {
        log.metadata['_ip'] = log.ip ? log.ip : null;

        // Note: This is for back-compat for logs that previously did not have namespaces.
        var namespace = '';
        if (log.namespace) {
          namespace = log.namespace.username || log.namespace.name;
        }

        log.metadata['namespace'] = log.metadata['namespace'] || namespace || '';
        return StringBuilderService.buildString(logDescriptions[log.kind] || log.kind, log.metadata,
                                                null, !full_description);
      };

      $scope.showExportLogs = function() {
        $scope.exportLogsInfo = {};
      };

      $scope.exportLogs = function(exportLogsInfo, callback) {
        if (!exportLogsInfo.urlOrEmail) {
          callback(false);
          return;
        }

        var exportURL = getUrl('exportlogs').toString();
        var runExport = Restangular.one(exportURL);

        var urlOrEmail = exportLogsInfo.urlOrEmail;
        var data = {};
        if (urlOrEmail.indexOf('http://') == 0 || urlOrEmail.indexOf('https://') == 0) {
          data['callback_url'] = urlOrEmail;
        } else {
          data['callback_email'] = urlOrEmail;
        }

        runExport.customPOST(data).then(function(resp) {
          bootbox.alert('Usage logs export queued with ID `' + resp['export_id'] + '`')
          callback(true);
        }, ApiService.errorDisplay('Could not start logs export', callback));
      };

      $scope.$watch('organization', update);
      $scope.$watch('user', update);
      $scope.$watch('repository', update);
      $scope.$watch('makevisible', update);

      $scope.$watch('options.logStartDate', update);
      $scope.$watch('options.logEndDate', update);
    }
  };

  return directiveDefinitionObject;
});
