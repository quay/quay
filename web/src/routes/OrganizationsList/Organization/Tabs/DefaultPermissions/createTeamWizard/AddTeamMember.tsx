import {
  Button,
  PageSection,
  TextContent,
  Text,
  TextVariants,
} from '@patternfly/react-core';
import {Table, Tbody, Td, Th, Thead, Tr} from '@patternfly/react-table';
import {ITeamMember} from 'src/hooks/UseMembers';
import {useEffect, useState} from 'react';
import AddTeamToolbar from 'src/routes/OrganizationsList/Organization/Tabs/DefaultPermissions/createTeamWizard/AddTeamToolbar';
import {
  useCreateRobotAccount,
  useFetchRobotAccounts,
} from 'src/hooks/useRobotAccounts';
import {getAccountTypeForMember} from 'src/libs/utils';
import {TrashIcon} from '@patternfly/react-icons';
import NameAndDescription from 'src/components/modals/robotAccountWizard/NameAndDescription';
import {useAlerts} from 'src/hooks/UseAlerts';
import {AlertVariant} from 'src/atoms/AlertState';
import ToggleDrawer from 'src/components/ToggleDrawer';

const memberAndRobotColNames = {
  teamMember: 'Team Member',
  account: 'Account',
};

export default function AddTeamMember(props: AddTeamMemberProps) {
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const [newRobotAccntName, setNewRobotAccntName] = useState('');
  const [newRobotAccntDescription, setNewRobotAccntDescription] = useState('');
  const {addAlert} = useAlerts();

  const {error, robots} = useFetchRobotAccounts(props.orgName);

  const [paginatedItems, setPaginatedItems] = useState<ITeamMember[]>(
    props.tableItems,
  );

  useEffect(() => {
    setPaginatedItems(
      props.tableItems?.slice(
        page * perPage - perPage,
        page * perPage - perPage + perPage,
      ),
    );
  }, [props.tableItems]);

  const {createNewRobot} = useCreateRobotAccount({
    namespace: props.orgName,
    onSuccess: (result) => {
      addAlert({
        variant: AlertVariant.Success,
        title: result,
      });
    },
    onError: (err) => {
      addAlert({
        variant: AlertVariant.Failure,
        title: err,
      });
    },
  });

  const addTeamMemberHandler = (memberName: string, isRobot: boolean) => {
    const robotExists = props.tableItems?.some(
      (item) => item.name === memberName,
    );
    if (!robotExists) {
      props.setTableItems((prev) => [
        ...prev,
        {
          name: memberName,
          kind: 'user',
          is_robot: isRobot,
        },
      ]);
      props.setAddedTeamMembers((prev) => [
        ...prev,
        {
          name: memberName,
          kind: 'user',
          is_robot: isRobot,
        },
      ]);
    }
  };

  const onCreateRobotAccount = async () => {
    await createNewRobot({
      namespace: props.orgName,
      robotname: newRobotAccntName,
      description: newRobotAccntDescription,
    });
    props.setDrawerExpanded(false);
    addTeamMemberHandler(`${props.orgName}+${newRobotAccntName}`, true);
  };

  const validateRobotName = () => {
    return /^[a-z][a-z0-9_]{1,254}$/.test(newRobotAccntName);
  };

  const drawerPanelContent = (
    <>
      <TextContent>
        <Text component={TextVariants.h1}>Provide a name and description</Text>
      </TextContent>
      <NameAndDescription
        name={newRobotAccntName}
        setName={setNewRobotAccntName}
        description={newRobotAccntDescription}
        setDescription={setNewRobotAccntDescription}
        nameLabel="Provide a name for your new robot account:"
        descriptionLabel="Provide an optional description for your new robot account:"
        helperText="Enter a description to provide extra information to your teammates about this new team account. Max length: 255"
        nameHelperText="Choose a name to inform your teammates about this robot account. Must match ^[a-z][a-z0-9_]{1,254}$."
        validateName={validateRobotName}
      />
      <div className="drawer-footer">
        <Button
          data-testid="create-robot-accnt-drawer-btn"
          variant="primary"
          onClick={onCreateRobotAccount}
          isDisabled={!validateRobotName()}
        >
          Add robot account
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
        drawerpanelContent={drawerPanelContent}
      />
    );
  }

  const handleDeleteTeamMember = (member: ITeamMember) => {
    props.setTableItems((prev) =>
      prev.filter((item) => member.name !== item.name),
    );

    // remove member if added to potential team member list
    props.setAddedTeamMembers((prev) =>
      prev.filter((item) => item.name !== member.name),
    );

    // Add to delete member list if member already exists in db
    props.setDeletedTeamMembers((prev) => {
      const memberExists = props?.allMembers.find(
        (currentMember) => currentMember.name === member.name,
      );
      if (memberExists && !prev.includes(memberExists)) {
        return [...prev, memberExists];
      }
    });
  };

  if (error) {
    return <>Unable to load members list</>;
  }

  return (
    <PageSection padding={{default: 'noPadding'}}>
      <AddTeamToolbar
        orgName={props.orgName}
        allItems={props.tableItems}
        page={page}
        setPage={setPage}
        perPage={perPage}
        setPerPage={setPerPage}
        robots={robots}
        addTeamMemberHandler={addTeamMemberHandler}
        setDrawerExpanded={props.setDrawerExpanded}
      >
        <Table aria-label="Selectable table" variant="compact">
          <Thead>
            <Tr>
              <Th>{memberAndRobotColNames.teamMember}</Th>
              <Th>{memberAndRobotColNames.account}</Th>
              <Th />
            </Tr>
          </Thead>
          <Tbody>
            {paginatedItems?.map((member, rowIndex) => (
              <Tr key={rowIndex}>
                <Td dataLabel={memberAndRobotColNames.teamMember}>
                  {member.name}
                </Td>
                <Td dataLabel={memberAndRobotColNames.account}>
                  {getAccountTypeForMember(member)}
                </Td>
                <Td>
                  <Button
                    icon={<TrashIcon />}
                    variant="plain"
                    onClick={() => {
                      handleDeleteTeamMember(member);
                    }}
                    data-testid={`${member.name}-delete-icon`}
                  />
                </Td>
              </Tr>
            ))}
          </Tbody>
        </Table>
      </AddTeamToolbar>
    </PageSection>
  );
}

interface AddTeamMemberProps {
  orgName: string;
  allMembers: ITeamMember[];
  tableItems: ITeamMember[];
  setTableItems: (robotAccnt: any) => void;
  addedTeamMembers: ITeamMember[];
  setAddedTeamMembers: (teams: any) => void;
  deletedTeamMembers: ITeamMember[];
  setDeletedTeamMembers: (teams: any) => void;
  isDrawerExpanded: boolean;
  setDrawerExpanded?: (boolean) => void;
}
