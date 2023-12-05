import {useEffect, useState} from 'react';
import {
  Modal,
  ModalVariant,
  TextContent,
  Text,
  TextVariants,
  AlertGroup,
  Alert,
  AlertActionCloseButton,
  WizardHeader,
  Wizard,
  WizardStep,
} from '@patternfly/react-core';
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
import NameAndDescription from './NameAndDescription';
import {RepoPermissionDropdownItems} from 'src/routes/RepositoriesList/RobotAccountsList';
import AddTeamMember from './AddTeamMember';
import Review from './ReviewTeam';
import ReviewAndFinishFooter from './ReviewAndFinishFooter';
import {useAddRepoPermissionToTeam} from 'src/hooks/UseTeams';
import {useAlerts} from 'src/hooks/UseAlerts';
import {AlertVariant} from 'src/atoms/AlertState';

export const CreateTeamWizard = (props: CreateTeamWizardProps): JSX.Element => {
  const [selectedRepoPerms, setSelectedRepoPerms] = useRecoilState(
    selectedRobotReposPermissionState,
  );
  const [selectedRepos, setSelectedRepos] = useRecoilState(
    selectedRobotReposState,
  );
  const [isDrawerExpanded, setDrawerExpanded] = useState(false);
  const [addedTeamMembers, setAddedTeamMembers] = useState<ITeamMember[]>([]);
  const [deletedTeamMembers, setDeletedTeamMembers] = useState<ITeamMember[]>(
    [],
  );
  const {addAlert} = useAlerts();

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
  } = useAddMembersToTeam(props.orgName, {
    onSuccess: () => {
      addAlert({
        variant: AlertVariant.Success,
        title: 'Successfully added members to team',
      });
    },
    onError: () => {
      addAlert({
        variant: AlertVariant.Failure,
        title: 'Unable to add members to team',
      });
    },
  });

  const {addRepoPermToTeam} = useAddRepoPermissionToTeam(
    props.orgName,
    props.teamName,
  );

  const {removeTeamMember} = useDeleteTeamMember(props.orgName);

  const onSubmitTeamWizard = async () => {
    // Add repo permission to team
    if (selectedRepoPerms?.length > 0) {
      selectedRepoPerms.map(async (repo) => {
        await addRepoPermToTeam({
          repoName: repo.name,
          newRole: repo.permission,
        });
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
    setSelectedRepoPerms([]);
  };

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
        onClose={() => {
          props.handleWizardToggle();
          setSelectedRepoPerms([]);
        }}
        showClose={false}
        hasNoBodyWrapper
      >
        <Wizard
          onClose={() => {
            props.handleWizardToggle();
            setSelectedRepoPerms([]);
          }}
          height={600}
          width={1170}
          header={
            <WizardHeader
              onClose={() => {
                props.handleWizardToggle();
                setSelectedRepoPerms([]);
              }}
              title="Create team"
              description=""
            />
          }
          footer={
            <Conditional if={!isDrawerExpanded}>
              <ReviewAndFinishFooter
                onSubmit={onSubmitTeamWizard}
                canSubmit={props.teamName !== ''}
              />
            </Conditional>
          }
        >
          <WizardStep name="Name & Description" id="name-and-description">
            <TextContent>
              <Text component={TextVariants.h1}>Team name and description</Text>
            </TextContent>
            <NameAndDescription
              name={props.teamName}
              description={props.teamDescription}
              nameLabel="Team name for your new team"
              descriptionLabel="Team description for your new team"
            />
          </WizardStep>

          <WizardStep name="Add to repository (optional)" id="add-to-repo">
            <AddToRepository
              namespace={props.orgName}
              dropdownItems={RepoPermissionDropdownItems}
              repos={repos}
              selectedRepos={selectedRepos}
              setSelectedRepos={setSelectedRepos}
              selectedRepoPerms={selectedRepoPerms}
              setSelectedRepoPerms={setSelectedRepoPerms}
              isWizardStep
            />
          </WizardStep>

          <WizardStep
            name="Add team member (optional)"
            id="add-team-member"
            body={{hasNoPadding: isDrawerExpanded}}
          >
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
          </WizardStep>

          <WizardStep name="Review and Finish" id="review-and-finish">
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
          </WizardStep>
        </Wizard>
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
