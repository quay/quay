import {
  Alert,
  Modal,
  ModalVariant,
  Text,
  TextContent,
  TextVariants,
  Wizard,
} from '@patternfly/react-core';
import {SetStateAction, useState} from 'react';
import NameAndDescription from './robotAccountWizard/NameAndDescription';
import {useCreateRobotAccount} from 'src/hooks/useRobotAccounts';

import Footer from './robotAccountWizard/Footer';
import AddToTeam from './robotAccountWizard/AddToTeam';
import AddToRepository from './robotAccountWizard/AddToRepository';
import {addDisplayError} from 'src/resources/ErrorHandling';
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
import {useOrganizations} from 'src/hooks/UseOrganizations';
import {Entity} from 'src/resources/UserResource';

export default function CreateRobotAccountModal(
  props: CreateRobotAccountModalProps,
) {
  if (!props.isModalOpen) {
    return null;
  }

  // Fetching repos
  const {repos: repos, totalResults: repoCount} = useRepositories(
    props.orgName,
  );

  const [robotName, setRobotName] = useState('');
  const [robotDescription, setrobotDescription] = useState('');
  const [err, setErr] = useState<string>();
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
  const [loading, setLoading] = useState<boolean>(true);
  const [activeStep, setActiveStep] = useState<string>(
    'Robot name and description',
  );

  const {createNewRobot} = useCreateRobotAccount({
    namespace: props.namespace,
    onSuccess: (result) => {
      props.setAlerts((prevAlerts) => {
        return [
          ...prevAlerts,
          <Alert
            key={new Date().getTime()}
            variant="success"
            title={`Successfully created robot account with robot name: ${result['robotname']}`}
            timeout={5000}
          />,
        ];
      });
      handleModalToggle();
    },
    onError: (err) => {
      setErr(addDisplayError('Unable to create robot', err));
      props.setAlerts((prevAlerts) => {
        return [
          ...prevAlerts,
          <Alert
            key="alert"
            variant="danger"
            title="Unable to create robot"
            timeout={5000}
          />,
        ];
      });
    },
  });

  const {usernames} = useOrganizations();
  const isUserOrganization = usernames.includes(props.orgName);

  const onSubmit = async () => {
    const reposToUpdate = filteredRepos();
    await createNewRobot({
      namespace: props.namespace,
      robotname: robotName,
      description: robotDescription,
      isUser: isUserOrganization,
      reposToUpdate: reposToUpdate,
      selectedTeams: selectedTeams,
      robotDefaultPerm: robotDefaultPerm,
    });
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

  const handleStepChange = (step) => {
    setActiveStep(step.name);
  };

  const NameAndDescriptionStep = {
    name: 'Robot name and description',
    component: (
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
    ),
  };

  const AddToTeamStep = {
    name: 'Add to team (optional)',
    component: (
      <AddToTeam
        items={props.teams}
        orgName={props.orgName}
        isDrawerExpanded={isDrawerExpanded}
        setDrawerExpanded={setDrawerExpanded}
        selectedTeams={selectedTeams}
        setSelectedTeams={setSelectedTeams}
      />
    ),
  };

  const AddToRepoStep = {
    name: 'Add to repository (optional)',
    component: (
      <AddToRepository
        namespace={props.orgName}
        dropdownItems={props.RepoPermissionDropdownItems}
        repos={repos}
        selectedRepos={selectedRepos}
        setSelectedRepos={setSelectedRepos}
        selectedRepoPerms={selectedRepoPerms}
        setSelectedRepoPerms={setSelectedRepoPerms}
        wizardStep={true}
      />
    ),
  };

  const DefaultPermsStep = {
    name: 'Default permissions (optional)',
    component: (
      <DefaultPermissions
        robotName={robotName}
        repoPermissions={props.RepoPermissionDropdownItems}
        robotDefaultPerm={robotDefaultPerm}
        setRobotdefaultPerm={setRobotdefaultPerm}
      />
    ),
  };

  const ReviewAndFinishStep = {
    name: 'Review and Finish',
    component: (
      <ReviewAndFinish
        robotName={robotName}
        robotDescription={robotDescription}
        selectedTeams={selectedTeams}
        selectedRepos={filteredRepos()}
        robotdefaultPerm={robotDefaultPerm}
        userNamespace={isUserOrganization}
      />
    ),
  };

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
        titleId="robot-account-wizard-label"
        descriptionId="robot-account-wizard-description"
        title="Create robot account (organization/namespace)"
        description="Robot Accounts are named tokens that can be granted permissions on multiple repositories under this organization."
        steps={isUserOrganization ? UserWizardSteps : OrgWizardSteps}
        onClose={handleModalToggle}
        height={600}
        width={1170}
        footer={
          <Footer
            onSubmit={onSubmit}
            isDrawerExpanded={isDrawerExpanded}
            isDataValid={validateRobotName}
          />
        }
        hasNoBodyPadding={
          isDrawerExpanded && activeStep == 'Add to team (optional)'
        }
        onCurrentStepChanged={(step) => handleStepChange(step)}
      />
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
  setAlerts: (prev) => void;
}
