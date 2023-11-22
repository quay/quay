import {useEffect, useState} from 'react';
import {
  Dropdown,
  DropdownItem,
  DropdownList,
  MenuToggle,
  MenuToggleElement,
} from '@patternfly/react-core';
import {
  IDefaultPermission,
  useUpdateDefaultPermission,
} from 'src/hooks/UseDefaultPermissions';
import {repoPermissions} from './DefaultPermissionsList';
import {useAlerts} from 'src/hooks/UseAlerts';
import {AlertVariant} from 'src/atoms/AlertState';
import {titleCase} from 'src/libs/utils';

export default function DefaultPermissionsDropDown(
  props: DefaultPermissionsDropdownProps,
) {
  const [isOpen, setIsOpen] = useState(false);
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
      toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
        <MenuToggle
          ref={toggleRef}
          onClick={() => setIsOpen(!isOpen)}
          isExpanded={isOpen}
          data-testid={`${props.defaultPermission.createdBy}-permission-dropdown-toggle`}
        >
          {titleCase(props.defaultPermission.permission)}
        </MenuToggle>
      )}
      isOpen={isOpen}
      onOpenChange={(isOpen) => setIsOpen(isOpen)}
      shouldFocusToggleOnSelect
    >
      <DropdownList>
        {Object.keys(repoPermissions).map((key) => (
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
      </DropdownList>
    </Dropdown>
  );
}

interface DefaultPermissionsDropdownProps {
  orgName: string;
  defaultPermission: IDefaultPermission;
}
