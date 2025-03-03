import {useState} from 'react';
import {Link, useSearchParams} from 'react-router-dom';
import {
  Dropdown,
  DropdownItem,
  DropdownList,
  MenuToggle,
  MenuToggleElement,
} from '@patternfly/react-core';
import EllipsisVIcon from '@patternfly/react-icons/dist/esm/icons/ellipsis-v-icon';
import { ISuperuserUsers } from 'src/hooks/UseSuperuserUsers';

export default function SuperuserUsersKebab(props: SuperuserUsersKebabProps) {
  const [isKebabOpen, setIsKebabOpen] = useState<boolean>(false);
  const [searchParams] = useSearchParams();

  return (
    <Dropdown
      onSelect={() => setIsKebabOpen(!isKebabOpen)}
      toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
        <MenuToggle
          ref={toggleRef}
          id={`${props.user.username}-toggle-kebab`}
          data-testid={`${props.user.username}-toggle-kebab`}
          variant="plain"
          onClick={() => setIsKebabOpen(!isKebabOpen)}
          isExpanded={isKebabOpen}
        >
          <EllipsisVIcon />
        </MenuToggle>
      )}
      isOpen={isKebabOpen}
      onOpenChange={(isOpen) => setIsKebabOpen(isOpen)}
      shouldFocusToggleOnSelect
    >
      <DropdownList>
        <DropdownItem>
          <Link
            to={null}
            data-testid={`${props.user.username}-manage-team-member-option`}
          >
            Change E-mail address
          </Link>
        </DropdownItem>

        <DropdownItem
          onClick={null}
          data-testid={`${props.user.username}-set-repo-perms-option`}
        >
          Change Password
        </DropdownItem>

        <DropdownItem
          key="delete"
          onClick={props.onDeleteTeam}
          className="red-color"
          data-testid={`${props.user.username}-del-option`}
        >
          Delete User
        </DropdownItem>

        <DropdownItem
          key="delete"
          onClick={props.onDeleteTeam}
          data-testid={`${props.user.username}-del-option`}
        >
          Disable User
        </DropdownItem>

        <DropdownItem
          key="delete"
          onClick={props.onDeleteTeam}
          data-testid={`${props.user.username}-del-option`}
        >
          Take Ownership
        </DropdownItem>
      </DropdownList>
    </Dropdown>
  );
}

interface SuperuserUsersKebabProps {
  user: ISuperuserUsers;
  deSelectAll: () => void;
  onDeleteTeam: () => void;
}
