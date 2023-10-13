import {useState} from 'react';
import {
  Alert,
  AlertActionCloseButton,
  AlertGroup,
  Dropdown,
  DropdownItem,
  DropdownList,
  MenuToggle,
  MenuToggleElement,
} from '@patternfly/react-core';
import Conditional from 'src/components/empty/Conditional';
import {useUpdateRepositoryPermissions} from 'src/hooks/UseUpdateRepositoryPermissions';
import {RepoMember} from 'src/resources/RepositoryResource';
import {roles} from './Types';

export default function PermissionsDropdown({
  member,
}: PermissionsDropdownProps) {
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const {
    setPermissions,
    errorSetPermissions: error,
    resetSetRepoPermissions,
  } = useUpdateRepositoryPermissions(member.org, member.repo);

  return (
    <>
      <Conditional if={error}>
        <AlertGroup isToast isLiveRegion>
          <Alert
            variant={'danger'}
            title={`Unable to set permissions for ${member.name}`}
            actionClose={
              <AlertActionCloseButton onClose={resetSetRepoPermissions} />
            }
          />
        </AlertGroup>
      </Conditional>
      <Dropdown
        onSelect={() => setIsOpen(false)}
        toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
          <MenuToggle
            ref={toggleRef}
            onClick={() => setIsOpen(() => !isOpen)}
            isExpanded={isOpen}
          >
            {member.role}
          </MenuToggle>
        )}
        isOpen={isOpen}
        onOpenChange={(isOpen) => setIsOpen(isOpen)}
        shouldFocusToggleOnSelect
      >
        <DropdownList>
          {roles.map((role) => (
            <DropdownItem
              key={role.name}
              description={role.description}
              onClick={() =>
                setPermissions({members: member, newRole: role.role})
              }
            >
              {role.name}
            </DropdownItem>
          ))}
        </DropdownList>
      </Dropdown>
    </>
  );
}

export interface PermissionsDropdownProps {
  member: RepoMember;
}
