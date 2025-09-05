import {useState} from 'react';
import {
  Dropdown,
  DropdownItem,
  DropdownList,
  MenuToggle,
  MenuToggleElement,
  Tooltip,
} from '@patternfly/react-core';
import {CogIcon} from '@patternfly/react-icons';
import RenameOrganizationModal from './modals/RenameOrganizationModal';
import DeleteOrganizationModal from './modals/DeleteOrganizationModal';
import TakeOwnershipModal from './modals/TakeOwnershipModal';

export default function OrganizationOptionsKebab(
  props: OrganizationOptionsKebabProps,
) {
  const [isKebabOpen, setIsKebabOpen] = useState<boolean>(false);
  const [isRenameModalOpen, setIsRenameModalOpen] = useState<boolean>(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState<boolean>(false);
  const [isTakeOwnershipModalOpen, setIsTakeOwnershipModalOpen] =
    useState<boolean>(false);

  const handleMenuItemClick = (action: string) => {
    setIsKebabOpen(false);

    switch (action) {
      case 'Rename Organization':
        setIsRenameModalOpen(true);
        break;
      case 'Delete Organization':
        setIsDeleteModalOpen(true);
        break;
      case 'Take Ownership':
        setIsTakeOwnershipModalOpen(true);
        break;
      default:
        console.log(`${action} not yet implemented`);
    }
  };

  const organizationMenuItems = [
    <DropdownItem
      key="rename"
      onClick={() => handleMenuItemClick('Rename Organization')}
    >
      Rename Organization
    </DropdownItem>,
    <DropdownItem
      key="delete"
      onClick={() => handleMenuItemClick('Delete Organization')}
    >
      Delete Organization
    </DropdownItem>,
    <DropdownItem
      key="takeOwnership"
      onClick={() => handleMenuItemClick('Take Ownership')}
    >
      Take Ownership
    </DropdownItem>,
  ];

  const userMenuItems = [
    <DropdownItem
      key="changeEmail"
      onClick={() => handleMenuItemClick('Change E-mail Address')}
    >
      Change E-mail Address
    </DropdownItem>,
    <DropdownItem
      key="changePassword"
      onClick={() => handleMenuItemClick('Change Password')}
    >
      Change Password
    </DropdownItem>,
    <DropdownItem
      key="deleteUser"
      onClick={() => handleMenuItemClick('Delete User')}
    >
      Delete User
    </DropdownItem>,
    <DropdownItem
      key="disableUser"
      onClick={() => handleMenuItemClick('Disable User')}
    >
      Disable User
    </DropdownItem>,
    <DropdownItem
      key="takeOwnership"
      onClick={() => handleMenuItemClick('Take Ownership')}
    >
      Take Ownership
    </DropdownItem>,
  ];

  const menuItems = props.isUser ? userMenuItems : organizationMenuItems;

  return (
    <>
      <Tooltip content="Options">
        <Dropdown
          onSelect={() => setIsKebabOpen(!isKebabOpen)}
          toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
            <MenuToggle
              ref={toggleRef}
              id={`${props.name}-options-toggle`}
              data-testid={`${props.name}-options-toggle`}
              variant="plain"
              onClick={() => setIsKebabOpen(!isKebabOpen)}
              isExpanded={isKebabOpen}
            >
              <CogIcon />
            </MenuToggle>
          )}
          isOpen={isKebabOpen}
          onOpenChange={(isOpen) => setIsKebabOpen(isOpen)}
          popperProps={{
            enableFlip: true,
            position: 'right',
          }}
          shouldFocusToggleOnSelect
        >
          <DropdownList>{menuItems}</DropdownList>
        </Dropdown>
      </Tooltip>

      {/* Modals */}
      <RenameOrganizationModal
        isOpen={isRenameModalOpen}
        onClose={() => setIsRenameModalOpen(false)}
        organizationName={props.name}
      />
      <DeleteOrganizationModal
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        organizationName={props.name}
      />
      <TakeOwnershipModal
        isOpen={isTakeOwnershipModalOpen}
        onClose={() => setIsTakeOwnershipModalOpen(false)}
        organizationName={props.name}
        isUser={props.isUser}
      />
    </>
  );
}

interface OrganizationOptionsKebabProps {
  name: string;
  isUser: boolean;
}
