import {
  Modal,
  ModalVariant,
  Button,
  Title,
  Tabs,
  Tab,
  TabTitleText,
  Tooltip,
} from '@patternfly/react-core';
import {Table, Tbody, Td, Th, Thead, Tr} from '@patternfly/react-table';
import {useState} from 'react';
import {RepositoryBuildTrigger} from 'src/resources/BuildResource';
import BuildTriggerDescription from './BuildTriggerDescription';
import Conditional from 'src/components/empty/Conditional';
import DockerfileUploadBuild from './BuildHistoryStartBuildModalUploadDockerfile';

export default function StartBuildModal(props: StartNewBuildModalProps) {
  const [activeTabKey, setActiveTabKey] = useState<string | number>(0);
  const activteTriggers = props.triggers.filter((trigger) => trigger.is_active);
  return (
    <Modal
      id="start-build-modal"
      aria-label="Start a new build modal"
      isOpen={props.isOpen}
      onClose={() => props.onClose()}
      variant={ModalVariant.medium}
      style={{
        overflowX: 'visible',
        overflowY: 'visible',
      }}
    >
      <Title headingLevel="h4">Start Repository Build</Title>
      <Tabs
        activeKey={activeTabKey}
        onSelect={(_, eventKey) => setActiveTabKey(eventKey)}
        aria-label="Start a new build tabs"
        role="region"
      >
        <Tab
          eventKey={0}
          title={<TabTitleText>Invoke Build Trigger</TabTitleText>}
          aria-label="invoke build trigger tab"
        >
          <p>
            Manually running a build trigger provides the means for invoking a
            build trigger as-if called from the underlying service for the
            latest commit to a particular branch or tag.
          </p>
          <Table variant="compact">
            <Thead>
              <Tr>
                <Th>Trigger Description</Th>
                <Th>Branches/Tags</Th>
                <Th></Th>
              </Tr>
            </Thead>
            <Tbody>
              <Conditional if={activteTriggers?.length === 0}>
                <Tr>
                  <Td colSpan={3}>
                    <p>No build triggers available for this repository.</p>
                  </Td>
                </Tr>
              </Conditional>
              {activteTriggers.map((trigger) => (
                <Tr key={trigger.id}>
                  <Td>
                    <BuildTriggerDescription trigger={trigger} />
                  </Td>
                  <Td>{trigger?.config?.branchtag_regex || 'All'}</Td>
                  <Td>
                    <Conditional if={trigger.can_invoke && trigger.enabled}>
                      <a onClick={() => props.onSelectTrigger(trigger)}>
                        Run Trigger Now
                      </a>
                    </Conditional>
                    <Conditional if={!trigger.can_invoke}>
                      <Tooltip content="You do not have permission to run this trigger">
                        <span>No permission to run</span>
                      </Tooltip>
                    </Conditional>
                    <Conditional if={!trigger.enabled}>
                      <span>Trigger Disabled</span>
                    </Conditional>
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
          <br />
          <Button
            key="cancel"
            variant="primary"
            onClick={() => props.onClose()}
          >
            Cancel
          </Button>
        </Tab>
        <Tab
          eventKey={1}
          title={<TabTitleText>Upload Dockerfile</TabTitleText>}
          aria-label="upload dockerfile tab"
        >
          <DockerfileUploadBuild
            org={props.org}
            repo={props.repo}
            onClose={props.onClose}
          />
        </Tab>
      </Tabs>
    </Modal>
  );
}

interface StartNewBuildModalProps {
  org: string;
  repo: string;
  isOpen: boolean;
  onClose: () => void;
  triggers: RepositoryBuildTrigger[];
  onSelectTrigger: (trigger: RepositoryBuildTrigger) => void;
}
