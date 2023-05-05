import {Dropdown, DropdownItem, DropdownToggle} from '@patternfly/react-core';
import {useEffect, useState} from 'react';
import {AlertVariant} from 'src/atoms/AlertState';
import {useAlerts} from 'src/hooks/UseAlerts';
import {useUpdateTeamRole} from 'src/hooks/UseTeams';

export enum teamPermissions {
  Admin = 'admin',
  Member = 'member',
  Creator = 'creator',
}

export function TeamsRoleDropDown(props: TeamsRoleDropDownProps) {
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const {addAlert} = useAlerts();

  const {
    updateTeamRole,
    errorUpdateTeamRole: error,
    successUpdateTeamRole: success,
  } = useUpdateTeamRole(props.organizationName);

  useEffect(() => {
    if (error) {
      addAlert({
        variant: AlertVariant.Failure,
        title: `Unable to update role for team: ${props.teamName}`,
      });
    }
  }, [error]);

  useEffect(() => {
    if (success) {
      addAlert({
        variant: AlertVariant.Success,
        title: `Team role updated successfully for: ${props.teamName}`,
      });
    }
  }, [success]);

  return (
    <Dropdown
      data-testid={`${props.teamName}-team-dropdown`}
      onSelect={() => setIsOpen(false)}
      toggle={
        <DropdownToggle onToggle={() => setIsOpen(!isOpen)}>
          {props.teamRole.charAt(0).toUpperCase() + props.teamRole.slice(1)}
        </DropdownToggle>
      }
      isOpen={isOpen}
      dropdownItems={Object.keys(teamPermissions).map((key) => (
        <DropdownItem
          data-testid={`${props.teamName}-${key}`}
          key={key}
          onClick={() =>
            updateTeamRole({
              teamName: props.teamName,
              teamRole: teamPermissions[key],
            })
          }
        >
          {key}
        </DropdownItem>
      ))}
    />
  );
}

interface TeamsRoleDropDownProps {
  organizationName: string;
  teamName: string;
  teamRole: string;
}
