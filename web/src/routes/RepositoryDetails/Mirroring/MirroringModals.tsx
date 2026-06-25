import React from 'react';
import {AlertVariant} from 'src/contexts/UIContext';
import CreateRobotAccountModal from 'src/components/modals/CreateRobotAccountModal';
import {CreateTeamModal} from 'src/routes/OrganizationsList/Organization/Tabs/DefaultPermissions/createPermissionDrawer/CreateTeamModal';
import {Entity} from 'src/resources/UserResource';
import {RepoPermissionDropdownItems} from 'src/routes/RepositoriesList/RobotAccountsList';
import {validateTeamName} from 'src/libs/utils';
import {ITeams} from 'src/hooks/UseTeams';

interface MirroringModalsProps {
  // Robot modal props
  isCreateRobotModalOpen: boolean;
  setIsCreateRobotModalOpen: (open: boolean) => void;

  // Team modal props
  isCreateTeamModalOpen: boolean;
  setIsCreateTeamModalOpen: (open: boolean) => void;
  teamName: string;
  setTeamName: (name: string) => void;
  teamDescription: string;
  setTeamDescription: (description: string) => void;

  // Common props
  namespace: string;
  teams: ITeams[];

  // Callbacks
  onRobotCreated: (robot: Entity) => void;
  onTeamCreated: (team: Entity) => void;
  addAlert: (alert: {
    variant: AlertVariant;
    title: string;
    message?: string;
  }) => void;
}

export const MirroringModals: React.FC<MirroringModalsProps> = ({
  isCreateRobotModalOpen,
  setIsCreateRobotModalOpen,
  isCreateTeamModalOpen,
  setIsCreateTeamModalOpen,
  teamName,
  setTeamName,
  teamDescription,
  setTeamDescription,
  namespace,
  teams,
  onRobotCreated,
  onTeamCreated,
  addAlert,
}) => {
  return (
    <>
      {/* Robot Creation Modal */}
      <CreateRobotAccountModal
        isModalOpen={isCreateRobotModalOpen}
        handleModalToggle={() => setIsCreateRobotModalOpen(false)}
        orgName={namespace}
        teams={teams}
        RepoPermissionDropdownItems={RepoPermissionDropdownItems}
        setEntity={onRobotCreated}
        showSuccessAlert={(msg) =>
          addAlert({variant: AlertVariant.Success, title: msg})
        }
        showErrorAlert={(msg) =>
          addAlert({variant: AlertVariant.Failure, title: msg})
        }
      />

      {/* Team Creation Modal */}
      <CreateTeamModal
        teamName={teamName}
        setTeamName={setTeamName}
        description={teamDescription}
        setDescription={setTeamDescription}
        orgName={namespace}
        nameLabel="Provide a name for your new team:"
        descriptionLabel="Provide an optional description for your new team"
        helperText="Enter a description to provide extra information to your teammates about this team:"
        nameHelperText="Choose a name to inform your teammates about this team. Must match ^([a-z0-9]+(?:[._-][a-z0-9]+)*)$"
        isModalOpen={isCreateTeamModalOpen}
        handleModalToggle={() => setIsCreateTeamModalOpen(false)}
        validateName={validateTeamName}
        setAppliedTo={onTeamCreated}
      />
    </>
  );
};
