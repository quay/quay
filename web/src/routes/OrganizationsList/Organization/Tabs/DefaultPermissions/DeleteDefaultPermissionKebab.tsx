import {
  Dropdown,
  DropdownItem,
  KebabToggle,
} from '@patternfly/react-core/deprecated';
import {useEffect, useState} from 'react';
import {AlertVariant} from 'src/atoms/AlertState';
import {useAlerts} from 'src/hooks/UseAlerts';
import {
  IDefaultPermission,
  useDeleteDefaultPermission,
} from 'src/hooks/UseDefaultPermissions';

export default function DeleteDefaultPermissionKebab(
  props: DefaultPermissionsDropdownProps,
) {
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const {addAlert} = useAlerts();

  const {
    removeDefaultPermission,
    errorDeleteDefaultPermission: error,
    successDeleteDefaultPermission: success,
    resetDeleteDefaultPermission: reset,
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
      toggle={
        <KebabToggle
          data-testid={`${props.defaultPermission.createdBy}-toggle-kebab`}
          onToggle={() => {
            setIsOpen(!isOpen);
          }}
        />
      }
      isOpen={isOpen}
      dropdownItems={[
        <DropdownItem
          key="delete"
          onClick={() =>
            removeDefaultPermission({id: props.defaultPermission.id})
          }
          data-testid={`${props.defaultPermission.createdBy}-del-option`}
        >
          Delete Permission
        </DropdownItem>,
      ]}
      isPlain
    />
  );
}

interface DefaultPermissionsDropdownProps {
  orgName: string;
  defaultPermission: IDefaultPermission;
}
