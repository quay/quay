import {SetStateAction, useEffect, useState} from 'react';
import {
  ActionGroup,
  Alert,
  AlertActionCloseButton,
  Button,
  Divider,
  Form,
  FormGroup,
  Title,
} from '@patternfly/react-core';
import {
  Dropdown,
  DropdownItem,
  DropdownToggle,
  SelectGroup,
  SelectOption,
} from '@patternfly/react-core/deprecated';
import {DesktopIcon, UsersIcon} from '@patternfly/react-icons';
import Conditional from 'src/components/empty/Conditional';
import EntitySearch from 'src/components/EntitySearch';
import {useUpdateRepositoryPermissions} from 'src/hooks/UseUpdateRepositoryPermissions';
import {RepoMember, RepoRole} from 'src/resources/RepositoryResource';
import {Entity, getMemberType} from 'src/resources/UserResource';
import {roles} from './Types';
import {useFetchRobotAccounts} from 'src/hooks/useRobotAccounts';
import React from 'react';
import {ITeams} from 'src/hooks/UseTeams';
import {useOrganizations} from 'src/hooks/UseOrganizations';

export default function AddPermissions(props: AddPermissionsProps) {
  const [isPermissionOpen, setIsPermissionOpen] = useState<boolean>(false);
  const [role, setRole] = useState<RepoRole>(RepoRole.admin);
  const [errorFetchingEntities, setErrorFetchingEntities] =
    useState<boolean>(false);
  const {usernames} = useOrganizations();
  const isUserOrganization = usernames.includes(props.org);

  const {
    setPermissions,
    errorSetPermissions: errorSettingPermissions,
    successSetPermissions: success,
    resetSetRepoPermissions,
  } = useUpdateRepositoryPermissions(props.org, props.repo);

  // Get robots
  const {robots} = useFetchRobotAccounts(props.org);

  const creatorDefaultOptions = [
    <React.Fragment key="creator">
      <Conditional if={!isUserOrganization}>
        <SelectGroup label="Teams" key="group3">
          {props.teams?.map((t) => (
            <SelectOption
              data-testid={`${t.name}-team`}
              key={t.name}
              value={t.name}
              onClick={() => {
                props.setSelectedEntity({
                  is_robot: false,
                  name: t.name,
                  kind: 'team',
                });
              }}
            />
          ))}
        </SelectGroup>
        <Divider component="li" key={4} />
      </Conditional>
      <SelectGroup label="Robot accounts" key="robot-account-grp">
        {robots?.map((r) => (
          <SelectOption
            data-testid={`${r.name}-robot-accnt`}
            key={r.name}
            value={r.name}
            onClick={() => {
              props.setSelectedEntity({
                is_robot: true,
                name: r.name,
                kind: 'user',
                is_org_member: true,
              });
            }}
          />
        ))}
      </SelectGroup>
      <Divider component="li" key={5} />
      <Conditional if={!isUserOrganization}>
        <SelectOption
          data-testid="create-new-team-btn"
          key="Create team1"
          component="button"
          onClick={() => props.setIsTeamModalOpen(!props.isTeamModalOpen)}
          isPlaceholder
          isFocused
        >
          <UsersIcon /> &nbsp; Create team
        </SelectOption>
      </Conditional>
      <SelectOption
        data-testid="create-new-robot-accnt-btn"
        key="create-robot-account"
        component="button"
        onClick={() =>
          props.setIsCreateRobotModalOpen(!props.isCreateRobotModalOpen)
        }
        isPlaceholder
        isFocused
      >
        <DesktopIcon /> &nbsp; Create robot account
      </SelectOption>
    </React.Fragment>,
  ];

  const createPermission = () => {
    const member: RepoMember = {
      org: props.org,
      repo: props.repo,
      name: props.selectedEntity.name,
      type: getMemberType(props.selectedEntity),
      role: null,
    };
    setPermissions({members: member, newRole: role});
  };

  useEffect(() => {
    if (success) {
      resetSetRepoPermissions();
      props.closeDrawer();
    }
  }, [success]);

  return (
    <>
      <Title headingLevel="h3">Add Permission</Title>
      <Conditional if={errorFetchingEntities}>
        <Alert isInline variant="danger" title="Unable to lookup users" />
      </Conditional>
      <Conditional if={errorSettingPermissions}>
        <Alert
          isInline
          actionClose={
            <AlertActionCloseButton onClose={resetSetRepoPermissions} />
          }
          variant="danger"
          title="Unable to set permissions"
        />
      </Conditional>
      <Form id="add-permission-form">
        <FormGroup fieldId="user" label="Select a team or user" required>
          <EntitySearch
            org={props.org}
            onError={() => setErrorFetchingEntities(true)}
            includeTeams={!isUserOrganization}
            onSelect={(e: Entity) => props.setSelectedEntity(e)}
            defaultOptions={creatorDefaultOptions}
            placeholderText="Search for user, add/create robot account"
            value={props.selectedEntity?.name}
            onClear={props.setSelectedEntity}
          />
        </FormGroup>
        <FormGroup fieldId="permission" label="Select a permission" required>
          <Dropdown
            onSelect={() => setIsPermissionOpen(false)}
            toggle={
              <DropdownToggle
                onToggle={(_event, isOpen) => setIsPermissionOpen(isOpen)}
              >
                {role}
              </DropdownToggle>
            }
            isOpen={isPermissionOpen}
            dropdownItems={roles.map((role) => (
              <DropdownItem
                key={role.name}
                description={role.description}
                onClick={() => setRole(role.role)}
              >
                {role.name}
              </DropdownItem>
            ))}
          />
        </FormGroup>
        <ActionGroup>
          <Button
            isDisabled={props.selectedEntity == null}
            onClick={() => {
              createPermission();
            }}
            variant="primary"
          >
            Submit
          </Button>
        </ActionGroup>
      </Form>
    </>
  );
}

interface AddPermissionsProps {
  org: string;
  repo: string;
  teams: ITeams[];
  closeDrawer: () => void;
  isCreateRobotModalOpen: boolean;
  setIsCreateRobotModalOpen: React.Dispatch<SetStateAction<boolean>>;
  isTeamModalOpen: boolean;
  setIsTeamModalOpen: React.Dispatch<SetStateAction<boolean>>;
  selectedEntity: Entity;
  setSelectedEntity: React.Dispatch<SetStateAction<Entity>>;
}
