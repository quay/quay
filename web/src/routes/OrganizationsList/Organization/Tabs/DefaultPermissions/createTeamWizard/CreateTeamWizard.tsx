import {
  Modal,
  ModalVariant,
  TextContent,
  Text,
  TextVariants,
  Wizard,
  AlertGroup,
  Alert,
  AlertActionCloseButton,
} from '@patternfly/react-core';
import {useEffect, useState} from 'react';
import {
  ITeamMember,
  useAddMembersToTeam,
  useDeleteTeamMember,
  useFetchTeamMembersForOrg,
} from 'src/hooks/UseMembers';
import Conditional from 'src/components/empty/Conditional';
import AddToRepository from 'src/components/modals/robotAccountWizard/AddToRepository';
import {useRepositories} from 'src/hooks/UseRepositories';
import {useRecoilState} from 'recoil';
import {
  selectedRobotReposPermissionState,
  selectedRobotReposState,
} from 'src/atoms/RobotAccountState';
import {addRepoPermissionToTeam} from 'src/resources/DefaultPermissionResource';
import NameAndDescription from './NameAndDescription';
import {RepoPermissionDropdownItems} from 'src/routes/RepositoriesList/RobotAccountsList';
import AddTeamMember from './AddTeamMember';
import Review from './ReviewTeam';
import ReviewAndFinishFooter from './ReviewAndFinishFooter';

export const CreateTeamWizard = (props: CreateTeamWizardProps): JSX.Element => {
  const [selectedRepoPerms, setSelectedRepoPerms] = useRecoilState(
    selectedRobotReposPermissionState,
  );
  const [selectedRepos, setSelectedRepos] = useRecoilState(
    selectedRobotReposState,
  );
  const [isDrawerExpanded, setDrawerExpanded] = useState(false);
  const [activeStep, setActiveStep] = useState<string>('Name & Description');
  const [addedTeamMembers, setAddedTeamMembers] = useState<ITeamMember[]>([]);
  const [deletedTeamMembers, setDeletedTeamMembers] = useState<ITeamMember[]>(
    [],
  );

  // Fetching repos
  const {repos} = useRepositories(props.orgName);

  // Fetch team members
  const {allMembers} = useFetchTeamMembersForOrg(props.orgName, props.teamName);

  const [tableItems, setTableItems] = useState<ITeamMember[]>(allMembers || []);

  useEffect(() => {
    setTableItems(allMembers);
  }, [allMembers]);

  const filteredRepos = () => {
    return selectedRepoPerms.filter((repo) =>
      selectedRepos.includes(repo.name),
    );
  };

  const {
    addMemberToTeam,
    errorAddingMemberToTeam: error,
    successAddingMemberToTeam: success,
    resetAddingMemberToTeam: reset,
  } = useAddMembersToTeam(props.orgName);

  const {removeTeamMember} = useDeleteTeamMember(props.orgName);

  const onSubmitTeamWizard = async () => {
    // Add repo permission to team
    if (selectedRepoPerms?.length > 0) {
      selectedRepoPerms.map(async (repo) => {
        await addRepoPermissionToTeam(
          props.orgName,
          repo.name,
          props.teamName,
          repo.permission,
        );
      });
    }
    // add member to team
    if (addedTeamMembers?.length > 0) {
      addedTeamMembers.map(async (mem) => {
        await addMemberToTeam({team: props.teamName, member: mem.name});
      });
    }

    // delete member from team
    if (deletedTeamMembers?.length > 0) {
      deletedTeamMembers.map(async (mem) => {
        await removeTeamMember({
          teamName: props.teamName,
          memberName: mem.name,
        });
      });
    }
    props.handleWizardToggle();
  };

  const handleStepChange = (step) => {
    setActiveStep(step.name);
  };

  const steps = [
    {
      name: 'Name & Description',
      component: (
        <>
          <TextContent>
            <Text component={TextVariants.h1}>Team name and description</Text>
          </TextContent>
          <NameAndDescription
            name={props.teamName}
            description={props.teamDescription}
            nameLabel="Team name for your new team"
            descriptionLabel="Team description for your new team"
          />
        </>
      ),
    },
    {
      name: 'Add to repository (optional)',
      component: (
        <AddToRepository
          namespace={props.orgName}
          dropdownItems={RepoPermissionDropdownItems}
          repos={repos}
          selectedRepos={selectedRepos}
          setSelectedRepos={setSelectedRepos}
          selectedRepoPerms={selectedRepoPerms}
          setSelectedRepoPerms={setSelectedRepoPerms}
          wizardStep={true}
        />
      ),
    },
    {
      name: 'Add team member (optional)',
      component: (
        <>
          <Conditional if={!isDrawerExpanded}>
            <TextContent>
              <Text component={TextVariants.h1}>
                Add team member (optional)
              </Text>
            </TextContent>
          </Conditional>
          <AddTeamMember
            orgName={props.orgName}
            allMembers={allMembers}
            tableItems={tableItems}
            setTableItems={setTableItems}
            addedTeamMembers={addedTeamMembers}
            setAddedTeamMembers={setAddedTeamMembers}
            deletedTeamMembers={deletedTeamMembers}
            setDeletedTeamMembers={setDeletedTeamMembers}
            isDrawerExpanded={isDrawerExpanded}
            setDrawerExpanded={setDrawerExpanded}
          />
        </>
      ),
    },
    {
      name: 'Review and Finish',
      component: (
        <>
          <TextContent>
            <Text component={TextVariants.h1}>Review</Text>
          </TextContent>
          <Review
            orgName={props.orgName}
            teamName={props.teamName}
            description={props.teamDescription}
            addedTeamMembers={addedTeamMembers}
            selectedRepos={filteredRepos()}
          />
        </>
      ),
    },
  ];

  return (
    <>
      <Conditional if={error}>
        <AlertGroup isToast isLiveRegion>
          <Alert
            variant="danger"
            title={`Unable to add member to ${props.teamName} team`}
            actionClose={<AlertActionCloseButton onClose={reset} />}
          />
        </AlertGroup>
      </Conditional>
      <Conditional if={success}>
        <AlertGroup isToast isLiveRegion>
          <Alert
            variant="success"
            title={`Sucessfully added member to ${props.teamName} team`}
            actionClose={<AlertActionCloseButton onClose={reset} />}
          />
        </AlertGroup>
      </Conditional>
      <Modal
        id="create-team-modal"
        aria-label="CreateTeam"
        variant={ModalVariant.large}
        isOpen={props.isTeamWizardOpen}
        onClose={props.handleWizardToggle}
        showClose={false}
        hasNoBodyWrapper
      >
        <Wizard
          titleId="create-team-wizard-label"
          descriptionId="create-team-wizard-description"
          title="Create team"
          description=""
          steps={steps}
          onClose={props.handleWizardToggle}
          height={600}
          width={1170}
          footer={
            <Conditional if={!isDrawerExpanded}>
              <ReviewAndFinishFooter
                onSubmit={onSubmitTeamWizard}
                canSubmit={props.teamName !== ''}
              />
            </Conditional>
          }
          hasNoBodyPadding={
            isDrawerExpanded && activeStep === 'Add team member (optional)'
          }
          onCurrentStepChanged={(currentStep) => handleStepChange(currentStep)}
        />
      </Modal>
    </>
  );
};

interface CreateTeamWizardProps {
  teamName: string;
  teamDescription: string;
  isTeamWizardOpen: boolean;
  handleWizardToggle?: () => void;
  orgName: string;
}
