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
  IOAuthApplication,
  useDeleteOAuthApplication,
} from 'src/hooks/UseOAuthApplications';

export default function DeleteDefaultPermissionKebab(
  props: DefaultPermissionsDropdownProps,
) {
  const [isOpen, setIsOpen] = useState(false);
  const {addAlert} = useAlerts();

  const {
    removeOAuthApplication,
    errorDeleteOAuthApplication: error,
    successDeleteOAuthApplication: success,
  } = useDeleteOAuthApplication(props.orgName);

  useEffect(() => {
    if (error) {
      addAlert({
        variant: AlertVariant.Failure,
        title: `Error deleting oauth application: ${error}`,
      });
    }
  }, [error]);

  useEffect(() => {
    if (success) {
      addAlert({
        variant: AlertVariant.Success,
        title: `Successfully deleted oauth application: ${props.oauthApplication.name}`,
      });
    }
  }, [success]);

  return (
    <Dropdown
      onSelect={() => setIsOpen(!isOpen)}
      toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
        <MenuToggle
          ref={toggleRef}
          id={`${props.oauthApplication.name}-toggle-kebab`}
          data-testid={`${props.oauthApplication.name}-toggle-kebab`}
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
          onClick={() => removeOAuthApplication({perm: props.oauthApplication})}
          data-testid={`${props.oauthApplication.name}-del-option`}
        >
          Delete Permission
        </DropdownItem>
      </DropdownList>
    </Dropdown>
  );
}

interface DefaultPermissionsDropdownProps {
  orgName: string;
  oauthApplication: IOAuthApplication;
}
