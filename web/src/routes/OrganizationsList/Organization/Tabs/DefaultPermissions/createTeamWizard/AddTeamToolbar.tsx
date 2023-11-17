import {useState} from 'react';
import {
  Divider,
  SelectGroup,
  SelectOption,
  Toolbar,
  ToolbarContent,
  ToolbarItem,
} from '@patternfly/react-core';
import {DesktopIcon} from '@patternfly/react-icons';
import React from 'react';
import EntitySearch from 'src/components/EntitySearch';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';
import {ITeamMember} from 'src/hooks/UseMembers';
import {IRobot} from 'src/resources/RobotsResource';
import {Entity} from 'src/resources/UserResource';

export default function AddTeamToolbar(props: AddTeamToolbarProps) {
  const [error, setError] = useState<string>('');

  const searchRobotAccntOptions = [
    <React.Fragment key="searchRobot">
      <SelectGroup label="Robot accounts" key="group4">
        {props?.robots.map(({name}) => {
          return (
            <SelectOption
              data-testid={`${name}-robot-accnt`}
              key={name}
              value={name}
              onClick={() => props.addTeamMemberHandler(name, true)}
            >
              {name}
            </SelectOption>
          );
        })}
      </SelectGroup>
      <Divider component="li" key={5} />
      <SelectOption
        data-testid="create-new-robot-accnt-btn"
        key="Create robot account2"
        component="button"
        onClick={() => props.setDrawerExpanded(true)}
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
              id={'search-member-dropdown'}
              org={props.orgName}
              includeTeams={false}
              onSelect={(e: Entity) =>
                props.addTeamMemberHandler(e.name, false)
              }
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
  addTeamMemberHandler: (robotAccnt: string, isRobot: boolean) => void;
  setDrawerExpanded?: (boolean) => void;
}
