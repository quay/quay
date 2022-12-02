import {Dropdown, DropdownItem, DropdownToggle} from '@patternfly/react-core';
import {useEffect, useState} from 'react';
import {
  IDefaultPermission,
  useUpdateDefaultPermission,
} from 'src/hooks/UseDefaultPermissions';
import {repoPermissions} from './DefaultPermissionsList';
import {useAlerts} from 'src/hooks/UseAlerts';
import {AlertVariant} from 'src/atoms/AlertState';

export default function DefaultPermissionsDropDown(
  props: DefaultPermissionsDropdownProps,
) {
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const {addAlert} = useAlerts();

  const {
    setDefaultPermission,
    successSetDefaultPermission: success,
    errorSetDefaultPermission: error,
  } = useUpdateDefaultPermission(props.orgName);

  useEffect(() => {
    if (error) {
      addAlert({
        variant: AlertVariant.Failure,
        title: `Unable to update permission to: ${props.defaultPermission.appliedTo}`,
      });
    }
  }, [error]);

  useEffect(() => {
    if (success) {
      addAlert({
        variant: AlertVariant.Success,
        title: `Permission updated successfully to: ${props.defaultPermission.appliedTo}`,
      });
    }
  }, [success]);

  return (
    <Dropdown
      data-testid={`${props.defaultPermission.createdBy}-permission-dropdown`}
      onSelect={() => setIsOpen(false)}
      toggle={
        <DropdownToggle onToggle={() => setIsOpen(!isOpen)}>
          {props.defaultPermission.permission.charAt(0).toUpperCase() +
            props.defaultPermission.permission.slice(1)}
        </DropdownToggle>
      }
      isOpen={isOpen}
      dropdownItems={Object.keys(repoPermissions).map((key) => (
        <DropdownItem
          data-testid={`${props.defaultPermission.createdBy}-${key}`}
          key={repoPermissions[key]}
          onClick={() =>
            setDefaultPermission({
              id: props.defaultPermission.id,
              newRole: repoPermissions[key],
            })
          }
        >
          {repoPermissions[key]}
        </DropdownItem>
      ))}
    />
  );
}

interface DefaultPermissionsDropdownProps {
  orgName: string;
  defaultPermission: IDefaultPermission;
}
