import {useEffect, useState} from 'react';
import {
  Dropdown,
  DropdownItem,
  DropdownList,
  MenuToggle,
  MenuToggleElement,
} from '@patternfly/react-core';
import EllipsisVIcon from '@patternfly/react-icons/dist/esm/icons/ellipsis-v-icon';
import {AlertVariant} from 'src/atoms/AlertState';
import {useAlerts} from 'src/hooks/UseAlerts';
import {
  IDefaultPermission,
  useDeleteDefaultPermission,
} from 'src/hooks/UseDefaultPermissions';

export default function DeleteDefaultPermissionKebab(
  props: DefaultPermissionsDropdownProps,
) {
  const [isOpen, setIsOpen] = useState(false);
  const {addAlert} = useAlerts();

  const {
    removeDefaultPermission,
    errorDeleteDefaultPermission: error,
    successDeleteDefaultPermission: success,
  } = useDeleteDefaultPermission(props.orgName);

  useEffect(() => {
    if (error) {
      addAlert({
        variant: AlertVariant.Failure,
        title: `Unable to delete permissions created by: ${props.defaultPermission.createdBy}`,
      });
    }
  }, [error]);

  useEffect(() => {
    if (success) {
      addAlert({
        variant: AlertVariant.Success,
        title: `Permission created by: ${props.defaultPermission.createdBy} successfully deleted`,
      });
    }
  }, [success]);

  return (
    <Dropdown
      onSelect={() => setIsOpen(!isOpen)}
      toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
        <MenuToggle
          ref={toggleRef}
          id={`${props.defaultPermission.createdBy}-toggle-kebab`}
          data-testid={`${props.defaultPermission.createdBy}-toggle-kebab`}
          variant="plain"
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
        <DropdownItem
          onClick={() =>
            removeDefaultPermission({perm: props.defaultPermission})
          }
          data-testid={`${props.defaultPermission.createdBy}-del-option`}
        >
          Delete Permission
        </DropdownItem>
      </DropdownList>
    </Dropdown>
  );
}

interface DefaultPermissionsDropdownProps {
  orgName: string;
  defaultPermission: IDefaultPermission;
}
