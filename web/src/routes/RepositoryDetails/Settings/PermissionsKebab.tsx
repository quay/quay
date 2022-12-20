import {
  Alert,
  AlertActionCloseButton,
  AlertGroup,
  Dropdown,
  DropdownItem,
  KebabToggle,
} from '@patternfly/react-core';
import {useState} from 'react';
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
        toggle={
          <KebabToggle
            id={`${member.name}-toggle-kebab`}
            onToggle={() => {
              setIsOpen(!isOpen);
            }}
          />
        }
        isOpen={isOpen}
        dropdownItems={[
          <DropdownItem key="delete" onClick={() => deletePermissions(member)}>
            Delete Permission
          </DropdownItem>,
        ]}
        isPlain
      />
    </>
  );
}

interface PermissionsKebabProps {
  member: RepoMember;
}
