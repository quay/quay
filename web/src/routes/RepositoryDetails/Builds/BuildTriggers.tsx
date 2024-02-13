import {
  List,
  ListItem,
  Title,
  Toolbar,
  ToolbarContent,
  ToolbarItem,
} from '@patternfly/react-core';
import {Table, Tbody, Td, Th, Thead, Tr} from '@patternfly/react-table';
import BuildTriggerDescription from './BuildTriggerDescription';
import Conditional from 'src/components/empty/Conditional';
import {isNullOrUndefined} from 'src/libs/utils';
import Entity from 'src/components/Entity';
import BuildTriggerActions from './BuildTriggerActions';
import {ExclamationTriangleIcon} from '@patternfly/react-icons';
import BuildTriggerToggleModal from './BuildTriggerToggleModal';
import {useState} from 'react';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import InactiveTrigger from './BuildTriggersInactiveTriggerRow';
import CreateBuildTriggerDropdown from './BuildCreateTriggerDropdown';
import SetupBuildTriggerModal from './BuildTriggerSetupModal';
import {RepositoryDetails} from 'src/resources/RepositoryResource';
import {RepositoryBuildTrigger} from 'src/resources/BuildResource';

export default function BuildTriggers(props: BuildTriggersProps) {
  const config = useQuayConfig();
  const [isSetupTriggerOpen, setIsSetupTriggerOpen] = useState(
    !isNullOrUndefined(props.setupTriggerUuid),
  );
  const [triggerToggleOptions, setTriggerToggleOptions] = useState<{
    trigger_uuid: string;
    enabled: boolean;
    isOpen: boolean;
  }>({trigger_uuid: null, enabled: null, isOpen: false});

  const activeTriggers = props.triggers.filter(
    (trigger) => trigger.is_active === true,
  );
  const inActiveTriggers = props.triggers.filter(
    (trigger) => trigger.is_active == false,
  );

  return (
    <>
      <Toolbar>
        <ToolbarContent style={{paddingLeft: '1em', paddingTop: '1em'}}>
          <ToolbarItem>
            <Title headingLevel="h2">Build Triggers</Title>
          </ToolbarItem>
          <ToolbarItem align={{default: 'alignRight'}}>
            <CreateBuildTriggerDropdown
              namespace={props.org}
              repo={props.repo}
            />
          </ToolbarItem>
        </ToolbarContent>
      </Toolbar>
      <Conditional if={props.triggers.length > 0}>
        <Table aria-label="Repository build triggers table" variant="compact">
          <Thead>
            <Tr>
              <Th>Trigger Name</Th>
              <Th>Dockerfile Location</Th>
              <Th>Context Location</Th>
              <Th>Branches/Tags</Th>
              <Th>Pull Robot</Th>
              <Th>Tagging Options</Th>
              <Th></Th>
            </Tr>
          </Thead>
          {inActiveTriggers.map((trigger) => (
            <Tbody key={trigger.id}>
              <InactiveTrigger
                org={props.org}
                repo={props.repo}
                trigger_uuid={trigger.id}
              />
            </Tbody>
          ))}
          {activeTriggers.map((trigger) => (
            <Tbody key={trigger.id}>
              <Tr data-testid={`row-${trigger.id}`}>
                <Td data-label="trigger name">
                  <BuildTriggerDescription trigger={trigger} />
                </Td>
                <Td data-label="dockerfile path">
                  {trigger?.config?.dockerfile_path || '/Dockerfile'}
                </Td>
                <Td data-label="context">{trigger?.config?.context || '/'}</Td>
                <Td data-label="branchtag regex">
                  {trigger?.config?.branchtag_regex || 'All'}
                </Td>
                <Td data-label="pull robot">
                  <Conditional if={!isNullOrUndefined(trigger.pull_robot)}>
                    <Entity
                      type={trigger.pull_robot?.kind}
                      name={trigger.pull_robot?.name}
                      includeIcon
                    />
                  </Conditional>
                  <Conditional if={isNullOrUndefined(trigger.pull_robot)}>
                    (None)
                  </Conditional>
                </Td>
                <Td data-label="tagging options">
                  <List>
                    <Conditional
                      if={
                        trigger.config?.default_tag_from_ref === true ||
                        trigger.config?.default_tag_from_ref == null
                      }
                    >
                      <ListItem style={{marginTop: '0'}}>
                        Branch/tag name
                      </ListItem>
                    </Conditional>
                    <Conditional
                      if={
                        trigger.config.latest_for_default_branch === true ||
                        trigger.config.latest_for_default_branch == null
                      }
                    >
                      <ListItem style={{marginTop: '0'}}>
                        <code>latest</code> if default branch
                      </ListItem>
                    </Conditional>
                    {trigger.config?.tag_templates?.map((template) => {
                      return (
                        <ListItem key={template} style={{marginTop: '0'}}>
                          {template}
                        </ListItem>
                      );
                    })}
                  </List>
                </Td>
                <Td>
                  <BuildTriggerActions
                    org={props.org}
                    repo={props.repo}
                    trigger={trigger}
                    enabled={trigger.enabled}
                  />
                </Td>
              </Tr>
              <Conditional if={trigger.enabled === false}>
                <Tr isBorderRow={false}>
                  <Td colSpan={7}>
                    <Conditional if={trigger.disabled_reason == 'user_toggled'}>
                      <ExclamationTriangleIcon /> This build trigger is user
                      disabled and will not build.
                    </Conditional>
                    <Conditional
                      if={
                        trigger.disabled_reason == 'successive_build_failures'
                      }
                    >
                      <ExclamationTriangleIcon /> This build trigger was
                      automatically disabled due to successive failures.
                    </Conditional>
                    <Conditional
                      if={
                        trigger.disabled_reason ==
                        'successive_build_internal_errors'
                      }
                    >
                      <ExclamationTriangleIcon /> This build trigger was
                      automatically disabled due to successive internal errors.
                    </Conditional>
                    <Conditional
                      if={config?.config?.REGISTRY_STATE !== 'readonly'}
                    >
                      <a
                        onClick={() =>
                          setTriggerToggleOptions({
                            trigger_uuid: trigger.id,
                            enabled: trigger.enabled,
                            isOpen: true,
                          })
                        }
                      >
                        {' '}
                        Re-enable this trigger
                      </a>
                    </Conditional>
                  </Td>
                </Tr>
              </Conditional>
            </Tbody>
          ))}
        </Table>
      </Conditional>
      <Conditional if={props.triggers.length === 0}>
        <p style={{padding: '1em'}}>
          No build triggers defined. Build triggers invoke builds whenever the
          triggered condition is met (source control push, webhook, etc)
        </p>
      </Conditional>
      <BuildTriggerToggleModal
        org={props.org}
        repo={props.repo}
        trigger_uuid={triggerToggleOptions.trigger_uuid}
        isOpen={triggerToggleOptions.isOpen}
        onClose={() =>
          setTriggerToggleOptions({
            trigger_uuid: null,
            enabled: null,
            isOpen: false,
          })
        }
        enabled={triggerToggleOptions.enabled}
      />
      <SetupBuildTriggerModal
        org={props.org}
        repo={props.repo}
        isOpen={isSetupTriggerOpen}
        onClose={() => setIsSetupTriggerOpen(false)}
        triggerUuid={props.setupTriggerUuid}
        repoDetails={props.repoDetails}
      />
    </>
  );
}

interface BuildTriggersProps {
  org: string;
  repo: string;
  setupTriggerUuid?: string;
  repoDetails: RepositoryDetails;
  triggers: RepositoryBuildTrigger[];
}
