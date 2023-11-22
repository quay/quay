import {useEffect, useState} from 'react';
import {
  Dropdown,
  DropdownItem,
  DropdownList,
  MenuToggle,
  MenuToggleElement,
} from '@patternfly/react-core';
import {ITeamRepoPerms} from 'src/hooks/UseTeams';
import {RepoPermissionDropdownItems} from 'src/routes/RepositoriesList/RobotAccountsList';
import {titleCase} from 'src/libs/utils';

export function SetRepoPermForTeamRoleDropDown(
  props: SetRepoPermForTeamRoleDropDownProps,
) {
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const [dropdownValue, setDropdownValue] = useState<string>(
    props.repoPerm?.role,
  );

  const dropdownOnSelect = (roleName) => {
    setDropdownValue(roleName);
    props.updateModifiedRepoPerms(roleName?.toLowerCase(), props.repoPerm);
  };

  useEffect(() => {
    if (props?.isItemSelected) {
      dropdownOnSelect(props.selectedVal);
    }
  }, [props.selectedVal]);

  useEffect(() => {
    setDropdownValue(props.repoPerm?.role);
  }, [props.repoPerm?.role]);

  return (
    <Dropdown
      data-testid={`${props.repoPerm.repoName}-role-dropdown`}
      onSelect={() => setIsOpen(false)}
      toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
        <MenuToggle
          ref={toggleRef}
          onClick={() => setIsOpen(!isOpen)}
          isExpanded={isOpen}
          data-testid={`${props.repoPerm.repoName}-role-dropdown-toggle`}
        >
          {dropdownValue ? titleCase(dropdownValue) : 'None'}
        </MenuToggle>
      )}
      isOpen={isOpen}
      onOpenChange={(isOpen) => setIsOpen(isOpen)}
      shouldFocusToggleOnSelect
    >
      <DropdownList>
        {RepoPermissionDropdownItems.map((item) => (
          <DropdownItem
            data-testid={`${props.repoPerm.repoName}-${item.name}`}
            key={item.name}
            description={item.description}
            onClick={() => dropdownOnSelect(item.name)}
          >
            {item.name}
          </DropdownItem>
        ))}
      </DropdownList>
    </Dropdown>
  );
}

interface SetRepoPermForTeamRoleDropDownProps {
  organizationName: string;
  teamName: string;
  repoPerm: ITeamRepoPerms;
  updateModifiedRepoPerms: (role: string, repoPerm: ITeamRepoPerms) => void;
  isItemSelected?: boolean;
  selectedVal: string;
}
