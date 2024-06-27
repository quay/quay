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
import {ISuperuserOrgs} from 'src/hooks/UseSuperuserOrgs';

export default function SuperuserOrgsKebab(props: SuperuserOrgsKebabProps) {
  const [isKebabOpen, setIsKebabOpen] = useState<boolean>(false);
  const [searchParams] = useSearchParams();

  return (
    <Dropdown
      onSelect={() => setIsKebabOpen(!isKebabOpen)}
      toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
        <MenuToggle
          ref={toggleRef}
          id={`${props.org.name}-toggle-kebab`}
          data-testid={`${props.org.name}-toggle-kebab`}
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
            data-testid={`${props.org.name}-manage-team-member-option`}
          >
            Rename Organization
          </Link>
        </DropdownItem>

        <DropdownItem
          key="delete"
          onClick={props.onDeleteTeam}
          className="red-color"
          data-testid={`${props.org.name}-del-option`}
        >
          Delete Organization
        </DropdownItem>

        <DropdownItem
          key="delete"
          onClick={props.onDeleteTeam}
          className="red-color"
          data-testid={`${props.org.name}-del-option`}
        >
          Take Ownership
        </DropdownItem>
      </DropdownList>
    </Dropdown>
  );
}

interface SuperuserOrgsKebabProps {
  org: ISuperuserOrgs;
  deSelectAll: () => void;
  onDeleteTeam: () => void;
}
