import {
  ActionGroup,
  Alert,
  AlertActionCloseButton,
  Button,
  Dropdown,
  DropdownItem,
  DropdownToggle,
  Form,
  FormGroup,
  Title,
} from '@patternfly/react-core';
import {useEffect, useState} from 'react';
import Conditional from 'src/components/empty/Conditional';
import EntitySearch from 'src/components/EntitySearch';
import {useUpdateRepositoryPermissions} from 'src/hooks/UseUpdateRepositoryPermissions';
import {RepoMember, RepoRole} from 'src/resources/RepositoryResource';
import {Entity, getMemberType} from 'src/resources/UserResource';
import {roles} from './Types';

export default function AddPermissions(props: AddPermissionsProps) {
  const [isPermissionOpen, setIsPermissionOpen] = useState<boolean>(false);
  const [role, setRole] = useState<RepoRole>(RepoRole.admin);
  const [selectedEntity, setSelectedEntity] = useState<Entity>(null);
  const [errorFetchingEntities, setErrorFetchingEntities] =
    useState<boolean>(false);
  const {
    setPermissions,
    errorSetPermissions: errorSettingPermissions,
    successSetPermissions: success,
    resetSetRepoPermissions,
  } = useUpdateRepositoryPermissions(props.org, props.repo);

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
        <FormGroup fieldId="user" label="Select a team or user" required>
          <EntitySearch
            org={props.org}
            onError={() => setErrorFetchingEntities(true)}
            onSelect={(e: Entity) => setSelectedEntity(e)}
          />
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
            isDisabled={selectedEntity == null}
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
