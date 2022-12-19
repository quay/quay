import {
  ActionGroup,
  Alert,
  AlertActionCloseButton,
  AlertGroup,
  Button,
  Dropdown,
  DropdownItem,
  DropdownToggle,
  Form,
  FormGroup,
  Select,
  SelectOption,
  SelectVariant,
  Title,
} from '@patternfly/react-core';
import {useEffect, useState} from 'react';
import Conditional from 'src/components/empty/Conditional';
import {useEntities} from 'src/hooks/UseEntities';
import {useUpdateRepositoryPermissions} from 'src/hooks/UseUpdateRepositoryPermissions';
import {
  RepoMember,
  MemberType,
  RepoRole,
} from 'src/resources/RepositoryResource';
import {Entity} from 'src/resources/UserResource';
import {roles} from './Types';

export default function AddPermissions(props: AddPermissionsProps) {
  const [isUserOpen, setIsUserOpen] = useState<boolean>(false);
  const [isPermissionOpen, setIsPermissionOpen] = useState<boolean>(false);
  const [role, setRole] = useState<RepoRole>(RepoRole.admin);
  const {
    entities,
    isError: errorFetchingEntities,
    searchTerm,
    setSearchTerm,
  } = useEntities(props.org);
  const {
    setPermissions,
    errorSetPermissions: errorSettingPermissions,
    successSetPermissions: success,
    resetSetRepoPermissions,
  } = useUpdateRepositoryPermissions(props.org, props.repo);

  const filteredEntities = entities.filter((e) => e.name === searchTerm);
  const validInput = filteredEntities.length > 0;
  const selectedEntity =
    filteredEntities.length > 0 ? filteredEntities[0] : null;

  const getMemberType = (entity: Entity) => {
    if (entity.kind == MemberType.team) {
      return MemberType.team;
    } else if (entity.kind == MemberType.user && entity.is_robot) {
      return MemberType.robot;
    } else if (entity.kind == MemberType.user) {
      return MemberType.user;
    }
  };

  const createPermission = () => {
    const member: RepoMember = {
      org: props.org,
      repo: props.repo,
      name: selectedEntity.name,
      type: getMemberType(selectedEntity),
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
        <FormGroup fieldId="user" label="Select a user" required>
          <Select
            isOpen={isUserOpen}
            selections={searchTerm}
            onSelect={(e, value) => {
              setSearchTerm(value as string);
              setIsUserOpen(!isUserOpen);
            }}
            onToggle={() => {
              setIsUserOpen(!isUserOpen);
            }}
            variant={SelectVariant.typeahead}
            onTypeaheadInputChanged={(value) => {
              setSearchTerm(value);
            }}
            shouldResetOnSelect={true}
            onClear={() => {
              setSearchTerm('');
            }}
          >
            {entities.map((e) => (
              <SelectOption
                key={e.name}
                value={e.name}
                description={getMemberType(e)}
              />
            ))}
          </Select>
        </FormGroup>
        <FormGroup fieldId="permission" label="Select a permission" required>
          <Dropdown
            onSelect={() => setIsPermissionOpen(false)}
            toggle={
              <DropdownToggle
                onToggle={(isOpen) => setIsPermissionOpen(isOpen)}
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
            isDisabled={!validInput}
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
  closeDrawer: () => void;
}
