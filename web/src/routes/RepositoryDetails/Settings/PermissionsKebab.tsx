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
import EllipsisVIcon from '@patternfly/react-icons/dist/esm/icons/ellipsis-v-icon';
import Conditional from 'src/components/empty/Conditional';
import {useUpdateRepositoryPermissions} from 'src/hooks/UseUpdateRepositoryPermissions';
import {RepoMember} from 'src/resources/RepositoryResource';

export default function PermissionsKebab({member}: PermissionsKebabProps) {
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const {
    deletePermissions,
    errorDeletePermissions: error,
    resetDeleteRepoPermissions,
  } = useUpdateRepositoryPermissions(member.org, member.repo);

  const onSelect = () => {
    setIsOpen(false);
    const element = document.getElementById(`${member.name}-toggle-kebab`);
    element.focus();
  };

  return (
    <>
      <Conditional if={error}>
        <AlertGroup isToast isLiveRegion>
          <Alert
            variant="danger"
            title={`Unable to set permissions for ${member.name}`}
            actionClose={
              <AlertActionCloseButton onClose={resetDeleteRepoPermissions} />
            }
          />
        </AlertGroup>
      </Conditional>
      <Dropdown
        onSelect={onSelect}
        toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
          <MenuToggle
            ref={toggleRef}
            variant="plain"
            id={`${member.name}-toggle-kebab`}
            data-testid={`${member.name}-toggle-kebab`}
            onClick={() => setIsOpen(!isOpen)}
            isExpanded={isOpen}
          >
            <EllipsisVIcon />
          </MenuToggle>
        )}
        isOpen={isOpen}
        onOpenChange={(isOpen) => setIsOpen(isOpen)}
        shouldFocusToggleOnSelect
      >
        <DropdownList>
          <DropdownItem key="delete" onClick={() => deletePermissions(member)}>
            Delete Permission
          </DropdownItem>
        </DropdownList>
      </Dropdown>
    </>
  );
}

interface PermissionsKebabProps {
  member: RepoMember;
}
