import React from 'react';
import CreateRobotAccountModal from 'src/components/modals/CreateRobotAccountModal';
import {useFetchTeams} from 'src/hooks/UseTeams';
import {RepoPermissionDropdownItems} from 'src/routes/RepositoriesList/RobotAccountsList';
import {Entity} from 'src/resources/UserResource';

interface CreateRobotModalWrapperProps {
  isModalOpen: boolean;
  handleModalToggle: () => void;
  orgName: string;
  setEntity: (robot: Entity) => void;
  showSuccessAlert: (msg: string) => void;
  showErrorAlert: (msg: string) => void;
}

/**
 * Wraps CreateRobotAccountModal and fetches teams data.
 * This component is conditionally rendered by the parent,
 * so teams are only fetched when the modal is open.
 */
export const CreateRobotModalWrapper: React.FC<
  CreateRobotModalWrapperProps
> = ({
  isModalOpen,
  handleModalToggle,
  orgName,
  setEntity,
  showSuccessAlert,
  showErrorAlert,
}) => {
  const {teams} = useFetchTeams(orgName);

  return (
    <CreateRobotAccountModal
      isModalOpen={isModalOpen}
      handleModalToggle={handleModalToggle}
      orgName={orgName}
      teams={teams}
      RepoPermissionDropdownItems={RepoPermissionDropdownItems}
      setEntity={setEntity}
      showSuccessAlert={showSuccessAlert}
      showErrorAlert={showErrorAlert}
    />
  );
};
