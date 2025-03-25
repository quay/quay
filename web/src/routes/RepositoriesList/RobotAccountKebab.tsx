import {useState} from 'react';
import {
  Dropdown,
  DropdownItem,
  DropdownList,
  MenuToggle,
  MenuToggleElement,
} from '@patternfly/react-core';
import EllipsisVIcon from '@patternfly/react-icons/dist/esm/icons/ellipsis-v-icon';
import {IRobot} from 'src/resources/RobotsResource';

export default function RobotAccountKebab(props: RobotAccountKebabProps) {
  const [isOpen, setIsOpen] = useState<boolean>(false);

  const onSelect = () => {
    setIsOpen(false);
    const element = document.getElementById(
      `${props.robotAccount.name}-toggle-kebab`,
    );
    element.focus();
  };

  const onDelete = () => {
    props.setSelectedRobotAccount([props.robotAccount]);
    props.setDeleteModalOpen(true);
  };

  const onSetRepoPerms = () => {
    props.onSetRepoPermsClick(props.robotAccount, props.robotAccountRepos);
  };

  const onSetRobotFederation = () => {
    props.onSetRobotFederationClick(props.robotAccount);
  };

  return (
    <>
      <Dropdown
        onSelect={onSelect}
        toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
          <MenuToggle
            ref={toggleRef}
            variant="plain"
            id={`${props.robotAccount.name}-toggle-kebab`}
            data-testid={`${props.robotAccount.name}-toggle-kebab`}
            onClick={() => setIsOpen(!isOpen)}
            isExpanded={isOpen}
          >
            <EllipsisVIcon />
          </MenuToggle>
        )}
        isOpen={isOpen}
        onOpenChange={(isOpen) => setIsOpen(isOpen)}
        shouldFocusToggleOnSelect
        popperProps={{
          enableFlip: true,
          position: 'right',
        }}
      >
        <DropdownList>
          <DropdownItem
            onClick={() => onSetRepoPerms()}
            id={`${props.robotAccount.name}-set-repo-perms-btn`}
          >
            Set repository permissions
          </DropdownItem>
          <DropdownItem
            onClick={() => onSetRobotFederation()}
            id={`${props.robotAccount.name}-set-robot-federation-btn`}
          >
            Set robot federation
          </DropdownItem>
          <DropdownItem
            onClick={() => onDelete()}
            className="red-color"
            id={`${props.robotAccount.name}-del-btn`}
          >
            Delete
          </DropdownItem>
        </DropdownList>
      </Dropdown>
    </>
  );
}

interface RobotAccountKebabProps {
  namespace: string;
  robotAccount: IRobot;
  setError: (err) => void;
  deleteModal: () => object;
  deleteKebabIsOpen: boolean;
  setDeleteModalOpen: (open) => void;
  setSelectedRobotAccount: (robotAccount) => void;
  onSetRepoPermsClick: (robotAccount, repos) => void;
  onSetRobotFederationClick: (robotAccount) => void;
  robotAccountRepos: any[];
}
