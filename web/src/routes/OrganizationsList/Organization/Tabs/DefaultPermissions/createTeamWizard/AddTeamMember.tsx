import {
  Button,
  PageSection,
  TextContent,
  Text,
  TextVariants,
} from '@patternfly/react-core';
import {
  TableComposable,
  Tbody,
  Td,
  Th,
  Thead,
  Tr,
} from '@patternfly/react-table';
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
  const [perPage, setPerPage] = useState(10);
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

  const {createRobotAccntHook} = useCreateRobotAccount(props.orgName, {
    onSuccess: () => {
      addAlert({
        variant: AlertVariant.Success,
        title: `Successfully created new robot accnt: ${newRobotAccntName}`,
      });
    },
    onError: () => {
      addAlert({
        variant: AlertVariant.Failure,
        title: 'Failed to create new robot accnt',
      });
    },
  });

  const addTeamMemberHandler = (robotName) => {
    const robotExists = props.tableItems?.some(
      (item) => item.name === robotName,
    );
    if (!robotExists) {
      props.setTableItems((prev) => [
        ...prev,
        {
          name: robotName,
          kind: 'user',
          is_robot: true,
        },
      ]);
      props.setAddedTeamMembers((prev) => [
        ...prev,
        {
          name: robotName,
          kind: 'user',
          is_robot: true,
        },
      ]);
    }
  };

  const onCreateRobotAccount = async () => {
    await createRobotAccntHook({
      robotAccntName: newRobotAccntName,
      description: newRobotAccntDescription,
    });
    props.setDrawerExpanded(false);
    addTeamMemberHandler(`${props.orgName}+${newRobotAccntName}`);
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
    <>
      <PageSection>
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
          <TableComposable aria-label="Selectable table">
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
          </TableComposable>
        </AddTeamToolbar>
      </PageSection>
    </>
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
