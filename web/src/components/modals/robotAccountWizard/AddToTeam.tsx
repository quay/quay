import {
  TableComposable,
  Tbody,
  Td,
  Th,
  Thead,
  Tr,
} from '@patternfly/react-table';
import {
  PageSection,
  PanelFooter,
  ToggleGroup,
  ToggleGroupItem,
  ToggleGroupItemProps,
  Toolbar,
  ToolbarContent,
  ToolbarItem,
  DropdownItem,
  Button,
  Text,
  TextVariants,
  TextContent,
} from '@patternfly/react-core';
import React, {useEffect, useState} from 'react';
import {DesktopIcon} from '@patternfly/react-icons';
import ToggleDrawer from 'src/components/ToggleDrawer';
import NameAndDescription from 'src/components/modals/robotAccountWizard/NameAndDescription';
import {useTeams} from 'src/hooks/useTeams';
import {addDisplayError} from 'src/resources/ErrorHandling';
import TeamView from './TeamView';

export default function AddToTeam(props: AddToTeamProps) {
  const [newTeamName, setNewTeamName] = useState('');
  const [newTeamDescription, setNewTeamDescription] = useState('');
  const [err, setErr] = useState<string>();

  const {createNewTeamHook} = useTeams(props.namespace);

  const createNewTeam = () => {
    props.setDrawerExpanded(true);
  };

  const dropdownItems = [
    <DropdownItem
      key="separated action"
      component="button"
      icon={<DesktopIcon />}
      onClick={createNewTeam}
    >
      Create new team
    </DropdownItem>,
  ];

  const validateTeamName = () => {
    return /^[a-z][a-z0-9_]{1,254}$/.test(newTeamName);
  };

  const onCreateNewTeam = async () => {
    try {
      await createNewTeamHook({
        namespace: props.namespace,
        name: newTeamName,
        description: newTeamDescription,
      }).then(function () {
        setNewTeamName('');
        setNewTeamDescription('');
        props.setDrawerExpanded(false);
      });
    } catch (error) {
      console.error(error);
      setErr(addDisplayError('Unable to create team', error));
    }
  };

  const DrawerPanelContent = (
    <>
      <NameAndDescription
        name={newTeamName}
        setName={setNewTeamName}
        description={newTeamDescription}
        setDescription={setNewTeamDescription}
        nameLabel="Provide a name for your new team account:"
        descriptionLabel="Provide an optional description for your new team account:"
        helperText="Enter a description to provide extra information to your teammates about this new team account. Max length: 255"
        nameHelperText="Choose a name to inform your teammates about this new account. Must match ^[a-z][a-z0-9_]{1,254}$."
        validateName={validateTeamName}
      />
      <div className="drawer-footer">
        <Button
          variant="primary"
          onClick={onCreateNewTeam}
          isDisabled={!validateTeamName()}
        >
          Add team account
        </Button>
        <Button variant="link" onClick={() => props.setDrawerExpanded(false)}>
          Cancel
        </Button>
      </div>
    </>
  );

  if (props.isDrawerExpanded) {
    return (
      <ToggleDrawer
        isExpanded={props.isDrawerExpanded}
        setIsExpanded={props.setDrawerExpanded}
        drawerpanelContent={DrawerPanelContent}
      />
    );
  }

  return (
    <>
      <TextContent>
        <Text component={TextVariants.h1}>Add to team (optional)</Text>
      </TextContent>
      <TeamView
        items={props.items}
        selectedTeams={props.selectedTeams}
        setSelectedTeams={props.setSelectedTeams}
        showCheckbox={true}
        dropdownItems={dropdownItems}
        showToggleGroup={true}
        filterWithDropdown={true}
      />
    </>
  );
}

interface AddToTeamProps {
  items: any[];
  namespace: string;
  isDrawerExpanded: boolean;
  setDrawerExpanded?: (boolean) => void;
  selectedTeams?: any[];
  setSelectedTeams?: (teams) => void;
}
