import {
  ToggleGroup,
  ToggleGroupItem,
  ToggleGroupItemProps,
  Toolbar,
  ToolbarContent,
  ToolbarItem,
} from '@patternfly/react-core';
import {useState} from 'react';
import {useParams} from 'react-router-dom';
import TeamsViewList from './TeamsView/TeamsViewList';
import CollaboratorsViewList from './CollaboratorsView/CollaboratorsViewList';
import MembersViewList from './MembersView/MembersViewList';
import {CreateTeamModal} from '../DefaultPermissions/createPermissionDrawer/CreateTeamModal';
import {CreateTeamWizard} from '../DefaultPermissions/createTeamWizard/CreateTeamWizard';
import {validateTeamName} from 'src/libs/utils';
import Conditional from 'src/components/empty/Conditional';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {useOrganization} from 'src/hooks/UseOrganization';

export enum TableModeType {
  Teams = 'Teams',
  Members = 'Members',
  Collaborators = 'Collaborators',
}

export default function TeamsAndMembershipList() {
  // state variables for Create Team
  const [teamName, setTeamName] = useState('');
  const [teamDescription, setTeamDescription] = useState('');
  const [isTeamModalOpen, setIsTeamModalOpen] = useState<boolean>(false);
  const [isTeamWizardOpen, setIsTeamWizardOpen] = useState<boolean>(false);
  const {organizationName} = useParams();
  const config = useQuayConfig();
  const {organization} = useOrganization(organizationName);

  const [tableMode, setTableMode] = useState<TableModeType>(
    TableModeType.Teams,
  );

  const onTableModeChange: ToggleGroupItemProps['onChange'] = (event) => {
    const id = event.currentTarget.id;
    setTableMode(id);
    fetchTableItems();
  };

  const createTeamModal = (
    <CreateTeamModal
      teamName={teamName}
      setTeamName={setTeamName}
      description={teamDescription}
      setDescription={setTeamDescription}
      orgName={organizationName}
      nameLabel="Provide a name for your new team:"
      descriptionLabel="Provide an optional description for your new team"
      helperText="Enter a description to provide extra information to your teammates about this team:"
      nameHelperText="Choose a name to inform your teammates about this team. Must match ^([a-z0-9]+(?:[._-][a-z0-9]+)*)$"
      isModalOpen={isTeamModalOpen}
      handleModalToggle={() => {
        setIsTeamModalOpen(!isTeamModalOpen);
        setTableMode(TableModeType.Teams);
      }}
      handleWizardToggle={() => setIsTeamWizardOpen(!isTeamWizardOpen)}
      validateName={validateTeamName}
    />
  );

  const createTeamWizard = (
    <CreateTeamWizard
      teamName={teamName}
      teamDescription={teamDescription}
      isTeamWizardOpen={isTeamWizardOpen}
      handleWizardToggle={() => setIsTeamWizardOpen(!isTeamWizardOpen)}
      orgName={organizationName}
    />
  );

  const viewToggle = (
    <Toolbar>
      <ToolbarContent>
        <ToolbarItem>
          <ToggleGroup aria-label="Team and membership toggle view">
            <ToggleGroupItem
              text="Team View"
              buttonId={TableModeType.Teams}
              isSelected={tableMode == TableModeType.Teams}
              onChange={onTableModeChange}
            />
            <ToggleGroupItem
              text="Members View"
              buttonId={TableModeType.Members}
              isSelected={tableMode == TableModeType.Members}
              onChange={onTableModeChange}
              isDisabled={!organization.is_admin}
            />
            <ToggleGroupItem
              text="Collaborators View"
              buttonId={TableModeType.Collaborators}
              isSelected={tableMode == TableModeType.Collaborators}
              onChange={onTableModeChange}
              isDisabled={!organization.is_admin}
            />
          </ToggleGroup>
        </ToolbarItem>
      </ToolbarContent>
    </Toolbar>
  );

  const fetchTableItems = () => {
    const renderCreateTeam = (
      <>
        <Conditional if={isTeamModalOpen}>{createTeamModal}</Conditional>
        <Conditional if={isTeamWizardOpen}>{createTeamWizard}</Conditional>
      </>
    );

    if (tableMode == TableModeType.Teams) {
      return (
        <>
          {renderCreateTeam}
          <TeamsViewList
            organizationName={organizationName}
            handleModalToggle={() => setIsTeamModalOpen(!isTeamModalOpen)}
            isReadOnly={config?.registry_state === 'readonly'}
            isAdmin={organization.is_admin}
          >
            {viewToggle}
          </TeamsViewList>
        </>
      );
    } else if (tableMode == TableModeType.Members) {
      return (
        <>
          {renderCreateTeam}
          <MembersViewList
            organizationName={organizationName}
            handleModalToggle={() => setIsTeamModalOpen(!isTeamModalOpen)}
          >
            {viewToggle}
          </MembersViewList>
        </>
      );
    } else if (tableMode == TableModeType.Collaborators) {
      return (
        <>
          {renderCreateTeam}
          <CollaboratorsViewList
            organizationName={organizationName}
            handleModalToggle={() => setIsTeamModalOpen(!isTeamModalOpen)}
          >
            {viewToggle}
          </CollaboratorsViewList>
        </>
      );
    }
  };

  return fetchTableItems();
}
