import {
  Alert,
  AlertActionCloseButton,
  AlertGroup,
  Menu,
  MenuContent,
  MenuItem,
  MenuList,
} from '@patternfly/react-core';
import {useEffect} from 'react';
import Conditional from 'src/components/empty/Conditional';
import {useUpdateRepositoryPermissions} from 'src/hooks/UseUpdateRepositoryPermissions';
import {RepoMember} from 'src/resources/RepositoryResource';
import {roles} from './Types';

export default function ChangePermissions(props: ChangePermissionsProps) {
  const {
    setPermissions,
    errorSetPermissions: error,
    successSetPermissions: success,
    resetSetRepoPermissions,
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
            variant={'danger'}
            title={`Unable to set repository permissions`}
            actionClose={
              <AlertActionCloseButton onClose={resetSetRepoPermissions} />
            }
          />
        </AlertGroup>
      </Conditional>
      <MenuItem
        id="change-permissions-menu"
        flyoutMenu={
          <Menu key={1}>
            <MenuContent>
              <MenuList data-testid="change-permissions-menu-list">
                {roles.map((role) => (
                  <MenuItem
                    key={role.name}
                    description={role.description}
                    onClick={() =>
                      setPermissions({
                        members: props.selectedItems,
                        newRole: role.role,
                      })
                    }
                    style={{width: 'max-content'}}
                  >
                    {role.name}
                  </MenuItem>
                ))}
              </MenuList>
            </MenuContent>
          </Menu>
        }
        itemId="next-menu-root"
      >
        Change Permissions
      </MenuItem>
    </>
  );
}

export interface ChangePermissionsProps {
  org: string;
  repo: string;
  selectedItems: RepoMember[];
  deselectAll: () => void;
  setIsMenuOpen: (isOpen: boolean) => void;
}
