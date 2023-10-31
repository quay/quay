import {SetStateAction, useState} from 'react';
import {
  Modal,
  ModalVariant,
  Text,
  TextContent,
  TextVariants,
  Wizard,
  WizardHeader,
  WizardStep,
} from '@patternfly/react-core';
import NameAndDescription from './robotAccountWizard/NameAndDescription';
import {useCreateRobotAccount} from 'src/hooks/useRobotAccounts';

import Footer from './robotAccountWizard/Footer';
import AddToTeam from './robotAccountWizard/AddToTeam';
import AddToRepository from './robotAccountWizard/AddToRepository';
import DefaultPermissions from './robotAccountWizard/DefaultPermissions';
import ReviewAndFinish from './robotAccountWizard/ReviewAndFinish';
import {useRecoilState} from 'recoil';
import {selectedTeamsState} from 'src/atoms/TeamState';
import {
  selectedRobotDefaultPermission,
  selectedRobotReposState,
  selectedRobotReposPermissionState,
} from 'src/atoms/RobotAccountState';
import {useRepositories} from 'src/hooks/UseRepositories';
import {addDisplayError} from 'src/resources/ErrorHandling';
import {useOrganizations} from 'src/hooks/UseOrganizations';
import {Entity} from 'src/resources/UserResource';

export default function CreateRobotAccountModal(
  props: CreateRobotAccountModalProps,
) {
  if (!props.isModalOpen) {
    return null;
  }

  // Fetching repos
  const {repos: repos} = useRepositories(props.orgName);

  const [robotName, setRobotName] = useState('');
  const [robotDescription, setrobotDescription] = useState('');
  const [selectedRepoPerms, setSelectedRepoPerms] = useRecoilState(
    selectedRobotReposPermissionState,
  );
  const [selectedTeams, setSelectedTeams] = useRecoilState(selectedTeamsState);
  const [selectedRepos, setSelectedRepos] = useRecoilState(
    selectedRobotReposState,
  );
  const [robotDefaultPerm, setRobotdefaultPerm] = useRecoilState(
    selectedRobotDefaultPermission,
  );
  const [isDrawerExpanded, setDrawerExpanded] = useState(false);

  const {createNewRobot, addRepoPerms, addTeams, addDefaultPerms} =
    useCreateRobotAccount({
      namespace: props.orgName,
      onSuccess: (result) => {
        props.showSuccessAlert(result);
        handleModalToggle();
      },
      onError: (err) => {
        props.showErrorAlert(addDisplayError('Error', err));
      },
    });

  const {usernames} = useOrganizations();
  const isUserOrganization = usernames.includes(props.orgName);

  const onSubmit = async () => {
    const reposToUpdate = filteredRepos();
    const created = await createNewRobot({
      namespace: props.orgName,
      robotname: robotName,
      description: robotDescription,
      isUser: isUserOrganization,
    });

    if (!created || created['name'] == '') {
      return;
    }

    if (reposToUpdate) {
      await addRepoPerms({
        namespace: props.orgName,
        robotname: robotName,
        isUser: isUserOrganization,
        reposToUpdate: reposToUpdate,
      });
    }
    if (selectedTeams) {
      await addTeams({
        namespace: props.orgName,
        robotname: robotName,
        selectedTeams: selectedTeams,
      });
    }
    if (robotDefaultPerm && robotDefaultPerm != 'None') {
      await addDefaultPerms({
        namespace: props.orgName,
        robotname: robotName,
        robotDefaultPerm: robotDefaultPerm,
      });
    }

    if (props?.setEntity) {
      props.setEntity({
        is_robot: true,
        name: `${props.orgName}+${robotName}`,
        kind: 'user',
        is_org_member: true,
      });
    }
  };

  // addDefaultPermsForRobotMutator
  const validateRobotName = () => {
    return /^[a-z][a-z0-9_]{1,254}$/.test(robotName);
  };

  const handleModalToggle = () => {
    // clear selected states
    setSelectedRepos([]);
    setSelectedTeams([]);
    setSelectedRepoPerms([]);
    setRobotdefaultPerm('');

    props.handleModalToggle();
  };

  const filteredRepos = () => {
    return selectedRepoPerms.filter((repo) =>
      selectedRepos.includes(repo.name),
    );
  };

  const NameAndDescriptionStep = (
    <WizardStep
      name="Robot name and description"
      id="robot-name-and-desc"
      key="robot-name-and-desc"
    >
      <>
        <TextContent>
          <Text component={TextVariants.h1}>
            Provide robot account name and description
          </Text>
        </TextContent>
        <NameAndDescription
          name={robotName}
          setName={setRobotName}
          description={robotDescription}
          setDescription={setrobotDescription}
          nameLabel="Provide a name for your robot account:"
          descriptionLabel="Provide an optional description for your new robot:"
          helperText="Enter a description to provide extra information to your teammates about this robot account. Max length: 255"
          nameHelperText="Choose a name to inform your teammates about this robot account. Must match ^[a-z][a-z0-9_]{1,254}$."
          validateName={validateRobotName}
        />
      </>
    </WizardStep>
  );

  const AddToTeamStep = (
    <WizardStep
      name="Add to team (optional)"
      id="add-to-team"
      key="add-to-team"
      body={{hasNoPadding: isDrawerExpanded}}
    >
      <AddToTeam
        items={props.teams}
        orgName={props.orgName}
        isDrawerExpanded={isDrawerExpanded}
        setDrawerExpanded={setDrawerExpanded}
        selectedTeams={selectedTeams}
        setSelectedTeams={setSelectedTeams}
        isWizardStep
      />
    </WizardStep>
  );

  const AddToRepoStep = (
    <WizardStep
      name="Add to repository (optional)"
      id="add-to-repo"
      key="add-to-repo"
    >
      <AddToRepository
        namespace={props.orgName}
        dropdownItems={props.RepoPermissionDropdownItems}
        repos={repos}
        selectedRepos={selectedRepos}
        setSelectedRepos={setSelectedRepos}
        selectedRepoPerms={selectedRepoPerms}
        setSelectedRepoPerms={setSelectedRepoPerms}
        isWizardStep
      />
    </WizardStep>
  );

  const DefaultPermsStep = (
    <WizardStep
      name="Default permissions (optional)"
      id="default-permissions"
      key="default-permissions"
    >
      <DefaultPermissions
        robotName={robotName}
        repoPermissions={props.RepoPermissionDropdownItems}
        robotDefaultPerm={robotDefaultPerm}
        setRobotdefaultPerm={setRobotdefaultPerm}
      />
    </WizardStep>
  );

  const ReviewAndFinishStep = (
    <WizardStep
      name="Review and Finish"
      id="review-and-finish"
      key="review-and-finish"
    >
      <ReviewAndFinish
        robotName={robotName}
        robotDescription={robotDescription}
        selectedTeams={selectedTeams}
        selectedRepos={filteredRepos()}
        robotdefaultPerm={robotDefaultPerm}
        userNamespace={isUserOrganization}
      />
    </WizardStep>
  );

  const OrgWizardSteps = [
    NameAndDescriptionStep,
    AddToTeamStep,
    AddToRepoStep,
    DefaultPermsStep,
    ReviewAndFinishStep,
  ];
  const UserWizardSteps = [
    NameAndDescriptionStep,
    AddToRepoStep,
    ReviewAndFinishStep,
  ];

  return (
    <Modal
      id="create-robot-account-modal"
      aria-label="CreateRobotAccount"
      variant={ModalVariant.large}
      isOpen={props.isModalOpen}
      onClose={handleModalToggle}
      showClose={false}
      hasNoBodyWrapper
    >
      <Wizard
        onClose={handleModalToggle}
        height={600}
        width={1170}
        header={
          <WizardHeader
            onClose={handleModalToggle}
            title="Create robot account (organization/namespace)"
            description="Robot Accounts are named tokens that can be granted permissions on multiple repositories under this organization."
          />
        }
        footer={
          <Footer
            onSubmit={onSubmit}
            isDrawerExpanded={isDrawerExpanded}
            isDataValid={validateRobotName}
          />
        }
      >
        {isUserOrganization ? UserWizardSteps : OrgWizardSteps}
      </Wizard>
    </Modal>
  );
}

interface CreateRobotAccountModalProps {
  isModalOpen: boolean;
  handleModalToggle?: () => void;
  orgName: string;
  teams: any[];
  RepoPermissionDropdownItems: any[];
  setEntity?: React.Dispatch<SetStateAction<Entity>>;
  showSuccessAlert: (msg: string) => void;
  showErrorAlert: (msg: string) => void;
}
