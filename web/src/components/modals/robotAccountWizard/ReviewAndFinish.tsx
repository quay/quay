import {
  TextContent,
  Text,
  TextVariants,
  TextInput,
  FormGroup,
  Form,
  Dropdown,
  DropdownToggle,
  ToggleGroup,
  ToggleGroupItem,
  ToggleGroupItemProps,
} from '@patternfly/react-core';
import {TableComposable, Tbody, Td, Tr} from '@patternfly/react-table';
import React, {useState} from 'react';

type TableModeType = 'Teams' | 'Repositories' | 'Default-permissions';

const TeamColumnNames = {
  name: 'Team',
  role: 'Role',
  members: 'Members',
  lastUpdated: 'Last Updated',
};

const RepoColumnNames = {
  name: 'Repository',
  permissions: 'Permissions',
  lastUpdated: 'Last Updated',
};

export default function ReviewAndFinish(props: ReviewAndFinishProps) {
  const [tableMode, setTableMode] = useState<TableModeType>('Teams');

  const onTableModeChange: ToggleGroupItemProps['onChange'] = (
    _isSelected,
    event,
  ) => {
    const id = event.currentTarget.id;
    setTableMode(id as TableModeType);
  };

  const fetchTableItems = () => {
    if (tableMode == 'Teams') {
      return fetchSelectedTeams();
    } else if (tableMode == 'Repositories') {
      return fetchSelectedRepos();
    } else if (tableMode == 'Default-permissions') {
      return fetchDefaultPerms();
    }
  };

  const fetchSelectedTeams = () => {
    return (
      <TableComposable aria-label="Selectable table">
        <Tbody>
          {props.selectedTeams.map((team, rowIndex) => (
            <Tr key={team.name}>
              <Td
                select={{
                  rowIndex,
                  isSelected: true,
                  disable: true,
                }}
              />
              <Td dataLabel={TeamColumnNames.name}>{team.name}</Td>
              <Td dataLabel={TeamColumnNames.role}>{team.role}</Td>
              <Td dataLabel={TeamColumnNames.members}>
                {team.member_count > 1
                  ? team.member_count + ' Members'
                  : team.member_count + ' Member'}
              </Td>
              <Td dataLabel={TeamColumnNames.lastUpdated}>
                {team.last_updated ? team.last_updated : 'Never'}
              </Td>
            </Tr>
          ))}
        </Tbody>
      </TableComposable>
    );
  };

  const fetchSelectedRepos = () => {
    return (
      <TableComposable aria-label="Selectable table">
        <Tbody>
          {props.selectedRepos.map((repo, rowIndex) => (
            <Tr key={repo.name}>
              <Td
                select={{
                  rowIndex,
                  isSelected: true,
                  disable: true,
                }}
              />
              <Td dataLabel={RepoColumnNames.name}>{repo.name}</Td>
              <Td dataLabel={RepoColumnNames.permissions}>
                <Dropdown
                  toggle={
                    <DropdownToggle id="toggle-disabled" isDisabled>
                      {repo.permission}
                    </DropdownToggle>
                  }
                />
              </Td>
              <Td dataLabel={RepoColumnNames.lastUpdated}>
                {repo.last_modified ? repo.last_modified : 'Never'}
              </Td>
            </Tr>
          ))}
        </Tbody>
      </TableComposable>
    );
  };

  const fetchDefaultPerms = () => {
    if (props.robotdefaultPerm == 'None') {
      return;
    }
    return (
      <>
        <Form>
          <FormGroup
            label="Applied To"
            fieldId="robot-name"
            isRequired
            disabled
            className="fit-content"
          >
            <TextInput
              value={props.robotName}
              type="text"
              aria-label="robot-name-value"
              isDisabled
            />
          </FormGroup>
          <FormGroup label="Permission" fieldId="robot-permission" isRequired />
          <Dropdown
            toggle={
              <DropdownToggle id="toggle-disabled" isDisabled>
                {props.robotdefaultPerm}
              </DropdownToggle>
            }
          />
        </Form>
      </>
    );
  };

  return (
    <>
      <TextContent>
        <Text component={TextVariants.h1}>Review and finish</Text>
      </TextContent>
      <Form>
        <FormGroup
          label="Provide a name for your robot account:"
          fieldId="robot-name"
          isRequired
          disabled
        >
          <TextInput
            value={props.robotName}
            type="text"
            aria-label="robot-name-value"
            isDisabled
            className="fit-content"
          />
        </FormGroup>
        <FormGroup
          label="Provide an optional description for your robot account:"
          fieldId="robot-description"
          isRequired
          disabled
          className="fit-content"
        >
          <TextInput
            value={props.robotDescription}
            type="text"
            aria-label="robot-description"
            isDisabled
          />
        </FormGroup>

        <ToggleGroup aria-label="Default with single selectable">
          <ToggleGroupItem
            text="Teams"
            buttonId="Teams"
            isSelected={tableMode === 'Teams'}
            onChange={onTableModeChange}
          />
          <ToggleGroupItem
            text="Repositories"
            buttonId="Repositories"
            isSelected={tableMode === 'Repositories'}
            onChange={onTableModeChange}
          />
          <ToggleGroupItem
            text="Default permissions"
            buttonId="Default-permissions"
            isSelected={tableMode === 'Default-permissions'}
            onChange={onTableModeChange}
          />
        </ToggleGroup>
      </Form>
      {fetchTableItems()}
    </>
  );
}

interface ReviewAndFinishProps {
  robotName: string;
  robotDescription: string;
  selectedTeams: any[];
  selectedRepos: any[];
  robotdefaultPerm: string;
}
