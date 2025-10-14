import {useState} from 'react';
import {Link, useSearchParams} from 'react-router-dom';
import {
  Dropdown,
  DropdownItem,
  DropdownList,
  MenuToggle,
  MenuToggleElement,
} from '@patternfly/react-core';
import EllipsisVIcon from '@patternfly/react-icons/dist/esm/icons/ellipsis-v-icon';
import {
  ISuperuserOrgs,
  useTakeOwnershipOfOrg,
  useUpdateOrgName,
} from 'src/hooks/UseSuperuserOrgs';
import {useAlerts} from 'src/hooks/UseAlerts';
import {AlertVariant} from 'src/atoms/AlertState';

export default function SuperuserOrgsKebab(props: SuperuserOrgsKebabProps) {
  const [isKebabOpen, setIsKebabOpen] = useState<boolean>(false);
  const {addAlert} = useAlerts();

  const {updateOrganizationName, errorUpdatingOrgName, successUpdatingOrgName} =
    useUpdateOrgName();

  const {changeOrgOwnership, loadingChangingOwnership, errorChangingOwnership} =
    useTakeOwnershipOfOrg({
      onSuccess: () => {
        addAlert({
          title: 'Successfully changed org ownership',
          variant: AlertVariant.Success,
          key: 'alert',
        });
      },
      onError: (err) => {
        addAlert({
          title: err.response.data.error_message,
          variant: AlertVariant.Failure,
          key: 'alert',
        });
      },
    });

  return (
    <Dropdown
      onSelect={() => setIsKebabOpen(!isKebabOpen)}
      toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
        <MenuToggle
          ref={toggleRef}
          id={`${props.org.name}-toggle-kebab`}
          data-testid={`${props.org.name}-toggle-kebab`}
          variant="plain"
          onClick={() => setIsKebabOpen(!isKebabOpen)}
          isExpanded={isKebabOpen}
        >
          <EllipsisVIcon />
        </MenuToggle>
      )}
      isOpen={isKebabOpen}
      onOpenChange={(isOpen) => setIsKebabOpen(isOpen)}
      shouldFocusToggleOnSelect
    >
      <DropdownList>
        <DropdownItem
          key="rename"
          onClick={() =>
            updateOrganizationName({updatedOrgName: props.org.name})
          }
          data-testid={`${props.org.name}-rename-option`}
        >
          Rename Organization
        </DropdownItem>

        <DropdownItem
          key="delete"
          onClick={props.onDeleteOrg}
          className="red-color"
          data-testid={`${props.org.name}-del-option`}
        >
          Delete Organization
        </DropdownItem>

        <DropdownItem
          key="ownership"
          onClick={async () => await changeOrgOwnership(props.org.name)}
          data-testid={`${props.org.name}-ownership-option`}
        >
          Take Ownership
        </DropdownItem>
      </DropdownList>
    </Dropdown>
  );
}

interface SuperuserOrgsKebabProps {
  org: ISuperuserOrgs;
  deSelectAll: () => void;
  onDeleteOrg: () => void;
}
