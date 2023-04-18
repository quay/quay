import {
  Alert,
  AlertActionCloseButton,
  AlertGroup,
  MenuItem,
} from '@patternfly/react-core';
import {useEffect} from 'react';
import Conditional from 'src/components/empty/Conditional';
import {useUpdateRepositoryPermissions} from 'src/hooks/UseUpdateRepositoryPermissions';
import {RepoMember} from 'src/resources/RepositoryResource';

export default function Delete(props: DeleteProps) {
  const {
    deletePermissions,
    errorDeletePermissions: error,
    successDeletePermissions: success,
    resetDeleteRepoPermissions,
  } = useUpdateRepositoryPermissions(props.org, props.repo);

  useEffect(() => {
    if (success) {
      props.deselectAll();
      props.setIsMenuOpen(false);
    }
  }, [success]);

  return (
    <>
      <Conditional if={error}>
        <AlertGroup isToast isLiveRegion>
          <Alert
            variant="danger"
            title="Unable to bulk delete repository permissions"
            actionClose={
              <AlertActionCloseButton onClose={resetDeleteRepoPermissions} />
            }
          />
        </AlertGroup>
      </Conditional>
      <MenuItem
        id="bulk-delete-permissions"
        onClick={() => {
          deletePermissions(props.selectedItems);
        }}
      >
        Delete
      </MenuItem>
    </>
  );
}

export interface DeleteProps {
  org: string;
  repo: string;
  selectedItems: RepoMember[];
  deselectAll: () => void;
  setIsMenuOpen: (isOpen: boolean) => void;
}
