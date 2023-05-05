import {Dropdown, DropdownItem, DropdownToggle} from '@patternfly/react-core';
import {useEffect, useState} from 'react';
import {ITeamRepoPerms} from 'src/hooks/UseTeams';
import {RepoPermissionDropdownItems} from 'src/routes/RepositoriesList/RobotAccountsList';

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
      toggle={
        <DropdownToggle onToggle={() => setIsOpen(!isOpen)}>
          {dropdownValue
            ? dropdownValue?.charAt(0).toUpperCase() + dropdownValue?.slice(1)
            : 'None'}
        </DropdownToggle>
      }
      isOpen={isOpen}
      dropdownItems={RepoPermissionDropdownItems.map((item) => (
        <DropdownItem
          data-testid={`${props.repoPerm.repoName}-${item.name}`}
          key={item.name}
          description={item.description}
          onClick={() => dropdownOnSelect(item.name)}
        >
          {item.name}
        </DropdownItem>
      ))}
    />
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
