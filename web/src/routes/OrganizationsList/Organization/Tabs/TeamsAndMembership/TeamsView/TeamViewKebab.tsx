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
import {ITeams} from 'src/hooks/UseTeams';
import {getTeamMemberPath} from 'src/routes/NavigationPath';

export default function TeamViewKebab(props: TeamViewKebabProps) {
  const [isKebabOpen, setIsKebabOpen] = useState<boolean>(false);
  const [searchParams] = useSearchParams();

  return (
    <Dropdown
      onSelect={() => setIsKebabOpen(!isKebabOpen)}
      toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
        <MenuToggle
          ref={toggleRef}
          id={`${props.team.name}-toggle-kebab`}
          data-testid={`${props.team.name}-toggle-kebab`}
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
            to={getTeamMemberPath(
              location.pathname,
              props.organizationName,
              props.team.name,
              searchParams.get('tab'),
            )}
            data-testid={`${props.team.name}-manage-team-member-option`}
          >
            Manage team members
          </Link>
        </DropdownItem>

        <DropdownItem
          onClick={props.onSelectRepo}
          data-testid={`${props.team.name}-set-repo-perms-option`}
        >
          Set repository permissions
        </DropdownItem>

        <DropdownItem
          key="delete"
          onClick={props.onDeleteTeam}
          className="red-color"
          data-testid={`${props.team.name}-del-option`}
        >
          Delete
        </DropdownItem>
      </DropdownList>
    </Dropdown>
  );
}

interface TeamViewKebabProps {
  organizationName: string;
  team: ITeams;
  deSelectAll: () => void;
  onSelectRepo: () => void;
  onDeleteTeam: () => void;
}
