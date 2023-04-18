import {
  Dropdown,
  DropdownItem,
  KebabToggle,
  DropdownPosition,
} from '@patternfly/react-core';
import {IRobot} from 'src/resources/RobotsResource';
import {useState} from 'react';

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
    props.setSelectedRobotAccount([props.robotAccount.name]);
    props.setDeleteModalOpen(true);
  };

  const onSetRepoPerms = () => {
    props.onSetRepoPermsClick(props.robotAccount, props.robotAccountRepos);
  };

  return (
    <>
      <Dropdown
        onSelect={onSelect}
        toggle={
          <KebabToggle
            id={`${props.robotAccount.name}-toggle-kebab`}
            onToggle={() => {
              setIsOpen(!isOpen);
            }}
          />
        }
        isOpen={isOpen}
        dropdownItems={[
          <DropdownItem
            key="delete"
            onClick={() => onDelete()}
            className="red-color"
            id={`${props.robotAccount.name}-del-btn`}
          >
            {props.deleteKebabIsOpen ? props.deleteModal() : null}
            Delete
          </DropdownItem>,
          <DropdownItem
            key="set-repo-perms"
            onClick={() => onSetRepoPerms()}
            id={`${props.robotAccount.name}-set-repo-perms-btn`}
          >
            {props.deleteKebabIsOpen ? props.deleteModal() : null}
            Set repository permissions
          </DropdownItem>,
        ]}
        isPlain
        position={DropdownPosition.right}
      />
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
  robotAccountRepos: any[];
}
