import {useEffect, useState} from 'react';
import {
  Dropdown,
  DropdownItem,
  DropdownList,
  MenuToggle,
  MenuToggleElement,
} from '@patternfly/react-core';
import {AlertVariant} from 'src/atoms/AlertState';
import {useAlerts} from 'src/hooks/UseAlerts';
import {useUpdateTeamDetails} from 'src/hooks/UseTeams';
import {titleCase} from 'src/libs/utils';

export enum teamPermissions {
  Admin = 'admin',
  Member = 'member',
  Creator = 'creator',
}

export function TeamsRoleDropDown(props: TeamsRoleDropDownProps) {
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const {addAlert} = useAlerts();

  const {
    updateTeamDetails,
    errorUpdateTeamDetails: error,
    successUpdateTeamDetails: success,
  } = useUpdateTeamDetails(props.organizationName);

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
      toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
        <MenuToggle
          ref={toggleRef}
          onClick={() => setIsOpen(!isOpen)}
          isExpanded={isOpen}
          data-testid={`${props.teamName}-team-dropdown-toggle`}
          isDisabled={!props.isAdmin || props.isReadOnly}
        >
          {titleCase(props.teamRole)}
        </MenuToggle>
      )}
      isOpen={isOpen}
      onOpenChange={(isOpen) => setIsOpen(isOpen)}
      shouldFocusToggleOnSelect
    >
      <DropdownList>
        {Object.keys(teamPermissions).map((key) => (
          <DropdownItem
            data-testid={`${props.teamName}-${key}`}
            key={key}
            onClick={() =>
              updateTeamDetails({
                teamName: props.teamName,
                teamRole: teamPermissions[key],
              })
            }
          >
            {key}
          </DropdownItem>
        ))}
      </DropdownList>
    </Dropdown>
  );
}

interface TeamsRoleDropDownProps {
  organizationName: string;
  teamName: string;
  teamRole: string;
  isReadOnly: boolean;
  isAdmin: boolean;
}
