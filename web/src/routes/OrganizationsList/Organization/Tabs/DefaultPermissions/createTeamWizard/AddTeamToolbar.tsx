import {
  Divider,
  Toolbar,
  ToolbarContent,
  ToolbarItem,
} from '@patternfly/react-core';
import {SelectGroup, SelectOption} from '@patternfly/react-core/deprecated';
import {DesktopIcon} from '@patternfly/react-icons';
import React from 'react';
import {useState} from 'react';
import EntitySearch from 'src/components/EntitySearch';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';
import {ITeamMember} from 'src/hooks/UseMembers';
import {IRobot} from 'src/resources/RobotsResource';

export default function AddTeamToolbar(props: AddTeamToolbarProps) {
  const [error, setError] = useState<string>('');

  const searchRobotAccntOptions = [
    <React.Fragment key="searchRobot">
      <SelectGroup label="Robot accounts" key="group4">
        {props?.robots.map((r) => {
          return (
            <SelectOption
              data-testid={`${r.name}-robot-accnt`}
              key={r.name}
              value={r.name}
              onClick={() => {
                props.addTeamMemberHandler(r.name);
              }}
            />
          );
        })}
      </SelectGroup>
      <Divider component="li" key={5} />
      <SelectOption
        data-testid="create-new-robot-accnt-btn"
        key="Create robot account2"
        component="button"
        onClick={() => props.setDrawerExpanded(true)}
        isPlaceholder
        isFocused
      >
        <DesktopIcon /> &nbsp; Create robot account
      </SelectOption>
    </React.Fragment>,
  ];

  return (
    <>
      <Toolbar>
        <ToolbarContent>
          <ToolbarItem variant="search-filter">
            <EntitySearch
              id={'search-robot-account-dropdown'}
              org={props.orgName}
              includeTeams={false}
              onSelect={() => undefined}
              onClear={() => undefined}
              onError={() => setError('Unable to look up robot accounts')}
              defaultOptions={searchRobotAccntOptions}
              placeholderText="Add a user, robot to the team"
            />
          </ToolbarItem>
          <ToolbarPagination
            itemsList={props.allItems}
            perPage={props.perPage}
            page={props.page}
            setPage={props.setPage}
            setPerPage={props.setPerPage}
          />
        </ToolbarContent>
      </Toolbar>
      {props.children}
    </>
  );
}

interface AddTeamToolbarProps {
  orgName?: string;
  allItems: ITeamMember[];
  page: number;
  setPage: (page: number) => void;
  perPage: number;
  setPerPage: (perPage: number) => void;
  children?: React.ReactNode;
  robots: IRobot[];
  addTeamMemberHandler: (robotAccnt: string) => void;
  setDrawerExpanded?: (boolean) => void;
}
