import {useState} from 'react';
import {
  Dropdown,
  DropdownItem,
  DropdownList,
  MenuToggle,
  MenuToggleElement,
} from '@patternfly/react-core';
import EllipsisVIcon from '@patternfly/react-icons/dist/esm/icons/ellipsis-v-icon';
import BuildTriggerToggleModal from './BuildTriggerToggleModal';
import BuildTriggerViewCredentialsModal from './BuildTriggerViewCredentialsModal';
import {RepositoryBuildTrigger} from 'src/resources/BuildResource';
import BuildTriggerDeleteModal from './BuildTriggerDeleteModal';

export default function BuildTriggerActions(props: BuildTriggerActionsProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isViewCredentialsModalOpen, setIsViewCredentialsModalOpen] =
    useState(false);
  const [isToggleTriggerModalOpen, setIsToggleTriggerModalOpen] =
    useState(false);
  const [isDeleteTriggerModalOpen, setIsDeleteTriggerModalOpen] =
    useState(false);

  const dropdownItems = [
    <DropdownItem
      key="view-credentials-action"
      onClick={() => {
        setIsOpen(false);
        setIsViewCredentialsModalOpen(true);
      }}
    >
      View Credentials
    </DropdownItem>,
    <DropdownItem
      key="toggle-trigger-action"
      onClick={() => {
        setIsOpen(false);
        setIsToggleTriggerModalOpen(true);
      }}
    >
      {props.enabled ? 'Disable Trigger' : 'Enable Trigger'}
    </DropdownItem>,
    <DropdownItem
      key="delete-trigger-action"
      onClick={() => {
        setIsOpen(false);
        setIsDeleteTriggerModalOpen(true);
      }}
      style={{color: 'red'}}
    >
      Delete Trigger
    </DropdownItem>,
  ];

  return (
    <>
      <Dropdown
        toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
          <MenuToggle
            ref={toggleRef}
            id="build-trigger-actions-kebab"
            data-testid="build-trigger-actions-kebab"
            aria-label="Build trigger actions kebab"
            variant="plain"
            onClick={() => setIsOpen(() => !isOpen)}
            isExpanded={isOpen}
          >
            <EllipsisVIcon />
          </MenuToggle>
        )}
        isOpen={isOpen}
        onOpenChange={(isOpen) => setIsOpen(isOpen)}
        popperProps={{position: 'right'}}
        shouldFocusToggleOnSelect
      >
        <DropdownList>{dropdownItems}</DropdownList>
      </Dropdown>
      <BuildTriggerToggleModal
        org={props.org}
        repo={props.repo}
        trigger_uuid={props.trigger?.id}
        isOpen={isToggleTriggerModalOpen}
        onClose={() => setIsToggleTriggerModalOpen(false)}
        enabled={props.enabled}
      />
      <BuildTriggerViewCredentialsModal
        trigger={props.trigger}
        isOpen={isViewCredentialsModalOpen}
        onClose={() => setIsViewCredentialsModalOpen(false)}
      />
      <BuildTriggerDeleteModal
        org={props.org}
        repo={props.repo}
        trigger_uuid={props.trigger?.id}
        isOpen={isDeleteTriggerModalOpen}
        onClose={() => setIsDeleteTriggerModalOpen(false)}
      />
    </>
  );
}

interface BuildTriggerActionsProps {
  org: string;
  repo: string;
  trigger: RepositoryBuildTrigger;
  enabled: boolean;
}
