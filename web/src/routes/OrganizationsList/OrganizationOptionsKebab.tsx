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
import ChangeEmailModal from './modals/ChangeEmailModal';
import ChangePasswordModal from './modals/ChangePasswordModal';
import DeleteUserModal from './modals/DeleteUserModal';
import ToggleUserStatusModal from './modals/ToggleUserStatusModal';
import {useSuperuserPermissions} from 'src/hooks/UseSuperuserPermissions';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';

export default function OrganizationOptionsKebab(
  props: OrganizationOptionsKebabProps,
) {
  const {canModify} = useSuperuserPermissions();
  const {user} = useCurrentUser();
  const [isKebabOpen, setIsKebabOpen] = useState<boolean>(false);

  // Check if this is the currently logged-in user
  const isCurrentUser = props.isUser && user?.username === props.name;

  // If cannot modify, return null (no actions allowed)
  // This handles: read-only mode, read-only superuser, and non-superusers
  if (!canModify) {
    return null;
  }
  const [isRenameModalOpen, setIsRenameModalOpen] = useState<boolean>(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState<boolean>(false);
  const [isTakeOwnershipModalOpen, setIsTakeOwnershipModalOpen] =
    useState<boolean>(false);

  // User modal states
  const [isChangeEmailModalOpen, setIsChangeEmailModalOpen] =
    useState<boolean>(false);
  const [isChangePasswordModalOpen, setIsChangePasswordModalOpen] =
    useState<boolean>(false);
  const [isDeleteUserModalOpen, setIsDeleteUserModalOpen] =
    useState<boolean>(false);
  const [isToggleUserStatusModalOpen, setIsToggleUserStatusModalOpen] =
    useState<boolean>(false);

  const handleMenuItemClick = (action: string) => {
    setIsKebabOpen(false);

    switch (action) {
      // Organization actions
      case 'Rename Organization':
        setIsRenameModalOpen(true);
        break;
      case 'Delete Organization':
        setIsDeleteModalOpen(true);
        break;
      case 'Take Ownership':
        setIsTakeOwnershipModalOpen(true);
        break;
      // User actions
      case 'Change E-mail Address':
        setIsChangeEmailModalOpen(true);
        break;
      case 'Change Password':
        setIsChangePasswordModalOpen(true);
        break;
      case 'Delete User':
        setIsDeleteUserModalOpen(true);
        break;
      case 'Toggle User Status':
        setIsToggleUserStatusModalOpen(true);
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

  // For the currently logged-in user, don't show user management actions
  // Only show Configure Quota (which will be added in phase 3)
  const userMenuItems = isCurrentUser
    ? [
        // Currently logged-in user - no actions shown (quota will be added in phase 3)
      ]
    : [
        // Other users - show all user management actions
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
          key="toggleStatus"
          onClick={() => handleMenuItemClick('Toggle User Status')}
        >
          {props.userEnabled ? 'Disable User' : 'Enable User'}
        </DropdownItem>,
        <DropdownItem
          key="deleteUser"
          onClick={() => handleMenuItemClick('Delete User')}
        >
          Delete User
        </DropdownItem>,
        <DropdownItem
          key="takeOwnership"
          onClick={() => handleMenuItemClick('Take Ownership')}
        >
          Take Ownership
        </DropdownItem>,
      ];

  const menuItems = props.isUser ? userMenuItems : organizationMenuItems;

  // Don't render kebab if there are no menu items
  if (menuItems.length === 0) {
    return null;
  }

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

      {/* Organization Modals */}
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

      {/* User Modals */}
      <ChangeEmailModal
        isOpen={isChangeEmailModalOpen}
        onClose={() => setIsChangeEmailModalOpen(false)}
        username={props.name}
      />
      <ChangePasswordModal
        isOpen={isChangePasswordModalOpen}
        onClose={() => setIsChangePasswordModalOpen(false)}
        username={props.name}
      />
      <DeleteUserModal
        isOpen={isDeleteUserModalOpen}
        onClose={() => setIsDeleteUserModalOpen(false)}
        username={props.name}
      />
      <ToggleUserStatusModal
        isOpen={isToggleUserStatusModalOpen}
        onClose={() => setIsToggleUserStatusModalOpen(false)}
        username={props.name}
        currentlyEnabled={props.userEnabled ?? true}
      />
    </>
  );
}

interface OrganizationOptionsKebabProps {
  name: string;
  isUser: boolean;
  userEnabled?: boolean; // Only used when isUser is true
}
