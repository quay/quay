import React, {useEffect} from 'react';
import {
  Button,
  DatePicker,
  Flex,
  FlexItem,
  Split,
  SplitItem,
} from '@patternfly/react-core';
import ExportLogsModal from './UsageLogsExportModal';
import './css/UsageLogs.scss';
import UsageLogsGraph from './UsageLogsGraph';
import {useQueryClient} from '@tanstack/react-query';
import {UsageLogsTable} from './UsageLogsTable';

interface UsageLogsProps {
  organization: string;
  repository: string;
  type: string;
}

function formatDate(date: string) {
  /**
   * change date string from y-m-d to m%d%y for api
   */
  const dates = date.split('-');
  const year = dates[0];
  const month = dates[1];
  const day = dates[2];

  return `${month}/${day}/${year}`;
}

export default function UsageLogs(props: UsageLogsProps) {
  const queryClient = useQueryClient();

  const maxDate = new Date();
  const minDate = new Date();
  minDate.setMonth(maxDate.getMonth() - 1);
  minDate.setDate(minDate.getDate() + 1);

  const [logStartDate, setLogStartDate] = React.useState<string>(
    formatDate(minDate.toISOString().split('T')[0]),
  );
  const [logEndDate, setLogEndDate] = React.useState<string>(
    formatDate(maxDate.toISOString().split('T')[0]),
  );

  const [chartHidden, setChartHidden] = React.useState<boolean>(false);

  useEffect(() => {
    queryClient.invalidateQueries({
      queryKey: [
        'usageLogs',
        'table',
        {
          org: props.organization,
          repo: props.repository ? props.repository : 'isOrg',
        },
      ],
    });
  }, [logStartDate, logEndDate]);

  const rangeValidator = (date: Date) => {
    if (date < minDate) {
      return 'Date is before the allowable range';
    } else if (date > maxDate) {
      return 'Date is after the allowable range';
    }
    return '';
  };

  return (
    <>
      <Flex direction={{default: 'column'}}>
        <FlexItem>
          <Split hasGutter className="usage-logs-header">
            <SplitItem>
              <Button
                variant="secondary"
                onClick={() => setChartHidden(!chartHidden)}
              >
                {chartHidden ? 'Show Chart' : 'Hide Chart'}
              </Button>
            </SplitItem>
            <SplitItem isFilled></SplitItem>
            <SplitItem>
              <DatePicker
                value={logStartDate}
                onChange={(_event, str, date) => {
                  setLogStartDate(formatDate(str));
                }}
                validators={[rangeValidator]}
              />
            </SplitItem>
            <SplitItem>
              <DatePicker
                value={logEndDate}
                onChange={(_event, str, date) => {
                  setLogEndDate(formatDate(str));
                }}
                validators={[rangeValidator]}
              />
            </SplitItem>
            <SplitItem>
              <ExportLogsModal
                organization={props.organization}
                repository={props.repository}
                starttime={logStartDate}
                endtime={logEndDate}
                type={props.type}
              />
            </SplitItem>
          </Split>
        </FlexItem>
        <FlexItem>
          {chartHidden ? null : (
            <UsageLogsGraph
              starttime={logStartDate}
              endtime={logEndDate}
              repo={props.repository}
              org={props.organization}
              type={props.type}
            />
          )}
        </FlexItem>
        <FlexItem>
          <UsageLogsTable
            starttime={logStartDate}
            endtime={logEndDate}
            repo={props.repository}
            org={props.organization}
            type={props.type}
          />
        </FlexItem>
      </Flex>
    </>
  );
}

export const logKinds = {
  user_create: 'Create user',
  user_delete: 'Delete user',
  user_disable: 'Disable user',
  user_enable: 'Enable user',
  user_change_password: 'Change user password',
  user_change_email: 'Change user email',
  user_change_name: 'Change user name',
  user_change_invoicing: 'Change user invoicing',
  user_change_tag_expiration: 'Change time machine window',
  user_change_metadata: 'Change user metadata',
  user_generate_client_key: 'Generate Docker CLI password',
  account_change_plan: 'Change plan',
  account_change_cc: 'Update credit card',
  account_change_password: 'Change password',
  account_convert: 'Convert account to organization',
  create_robot: 'Create Robot Account',
  delete_robot: 'Delete Robot Account',
  create_repo: 'Create Repository',
  push_repo: 'Push to repository',
  repo_verb: 'Pull Repo Verb',
  pull_repo: 'Pull repository',
  delete_repo: 'Delete repository',
  change_repo_permission: 'Change repository permission',
  delete_repo_permission: 'Remove user permission from repository',
  change_repo_visibility: 'Change repository visibility',
  change_repo_trust: 'Change repository trust settings',
  add_repo_accesstoken: 'Create access token',
  delete_repo_accesstoken: 'Delete access token',
  set_repo_description: 'Change repository description',
  build_dockerfile: 'Build image from Dockerfile',
  delete_tag: 'Delete Tag',
  create_tag: 'Create Tag',
  move_tag: 'Move Tag',
  revert_tag: 'Restore Tag',
  org_create: 'Create organization',
  org_delete: 'Delete organization',
  org_change_email: 'Change organization email',
  org_change_invoicing: 'Change organization invoicing',
  org_change_tag_expiration: 'Change time machine window',
  org_change_name: 'Change organization name',
  org_create_team: 'Create team',
  org_delete_team: 'Delete team',
  org_add_team_member: 'Add team member',
  org_invite_team_member: 'Invite team member',
  org_delete_team_member_invite: 'Rescind team member invitation',
  org_remove_team_member: 'Remove team member',
  org_team_member_invite_accepted: 'Team invite accepted',
  org_team_member_invite_declined: 'Team invite declined',
  org_set_team_description: 'Change team description',
  org_set_team_role: 'Change team permission',
  create_prototype_permission: 'Create default permission',
  modify_prototype_permission: 'Modify default permission',
  delete_prototype_permission: 'Delete default permission',
  setup_repo_trigger: 'Setup build trigger',
  delete_repo_trigger: 'Delete build trigger',
  toggle_repo_trigger: 'Enable/disable build trigger',
  create_application: 'Create Application',
  update_application: 'Update Application',
  delete_application: 'Delete Application',
  reset_application_client_secret: 'Reset Client Secret',
  add_repo_notification: 'Add repository notification',
  delete_repo_notification: 'Delete repository notification',
  reset_repo_notification: 'Re-enable repository notification',
  regenerate_robot_token: 'Regenerate Robot Token',
  service_key_create: 'Create Service Key',
  service_key_approve: 'Approve Service Key',
  service_key_modify: 'Modify Service Key',
  service_key_delete: 'Delete Service Key',
  service_key_extend: 'Extend Service Key Expiration',
  service_key_rotate: 'Automatic rotation of Service Key',
  take_ownership: 'Take Namespace Ownership',
  manifest_label_add: 'Add Manifest Label',
  manifest_label_delete: 'Delete Manifest Label',
  change_tag_expiration: 'Change tag expiration',
  create_app_specific_token: 'Create external app token',
  revoke_app_specific_token: 'Revoke external app token',
  repo_mirror_enabled: 'Enable Repository Mirror',
  repo_mirror_disabled: 'Disable Repository Mirror',
  repo_mirror_config_changed: 'Changed Repository Mirror',
  repo_mirror_sync_started: 'Started Repository Mirror',
  repo_mirror_sync_failed: 'Repository Mirror sync failed',
  repo_mirror_sync_success: 'Repository Mirror sync success',
  repo_mirror_sync_now_requested: 'Repository Mirror immediate sync requested',
  repo_mirror_sync_tag_success: 'Repository Mirror tag sync successful',
  repo_mirror_sync_tag_failed: 'Repository Mirror tag sync failed',
  repo_mirror_sync_test_success: 'Test Repository Mirror success',
  repo_mirror_sync_test_failed: 'Test Repository Mirror failed',
  repo_mirror_sync_test_started: 'Test Repository Mirror started',
  create_proxy_cache_config: 'Create Proxy Cache Config',
  delete_proxy_cache_config: 'Delete Proxy Cache Config',
  start_build_trigger: 'Manual build trigger',
  cancel_build: 'Cancel build',
  login_success: 'Login success',
  permanently_delete_tag: 'Permanently Delete Tag',
  autoprune_tag_delete: 'Autoprune worker tag deletion',
  create_namespace_autoprune_policy: 'Create Namespace Autoprune Policy',
  update_namespace_autoprune_policy: 'Update Namespace Autoprune Policy',
  delete_namespace_autoprune_policy: 'Delete Namespace Autoprune Policy',
  create_repository_autoprune_policy: 'Create Repository Autoprune Policy',
  update_repository_autoprune_policy: 'Update Repository Autoprune Policy',
  delete_repository_autoprune_policy: 'Delete Repository Autoprune Policy',
  oauth_token_assigned: 'OAuth token assigned',
  enable_team_sync: 'Enable Team Sync',
  disable_team_sync: 'Disable Team Sync',
  export_logs_success: 'Export logs queued for delivery',
  export_logs_failure: 'Export logs failure',
};
