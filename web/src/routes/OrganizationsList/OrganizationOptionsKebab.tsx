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
import SendRecoveryEmailModal from './modals/SendRecoveryEmailModal';
import {useSuperuserPermissions} from 'src/hooks/UseSuperuserPermissions';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {ConfigureQuotaModal} from './modals/ConfigureQuotaModal';

export default function OrganizationOptionsKebab(
  props: OrganizationOptionsKebabProps,
) {
  const {canModify} = useSuperuserPermissions();
  const {user} = useCurrentUser();
  const quayConfig = useQuayConfig();
  const [isKebabOpen, setIsKebabOpen] = useState<boolean>(false);
  const [isRenameModalOpen, setIsRenameModalOpen] = useState<boolean>(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState<boolean>(false);
  const [isTakeOwnershipModalOpen, setIsTakeOwnershipModalOpen] =
    useState<boolean>(false);
  const [isChangeEmailModalOpen, setIsChangeEmailModalOpen] =
    useState<boolean>(false);
  const [isChangePasswordModalOpen, setIsChangePasswordModalOpen] =
    useState<boolean>(false);
  const [isSendRecoveryEmailModalOpen, setIsSendRecoveryEmailModalOpen] =
    useState<boolean>(false);
  const [isDeleteUserModalOpen, setIsDeleteUserModalOpen] =
    useState<boolean>(false);
  const [isToggleUserStatusModalOpen, setIsToggleUserStatusModalOpen] =
    useState<boolean>(false);
  const [isConfigureQuotaModalOpen, setIsConfigureQuotaModalOpen] =
    useState<boolean>(false);

  // Check if this is the currently logged-in user
  const isCurrentUser = props.isUser && user?.username === props.name;

  // Check if the row represents a superuser
  const isRowSuperuser = props.userSuperuser === true;

  // Determine authentication type
  const isDatabaseAuth = quayConfig?.config?.AUTHENTICATION_TYPE === 'Database';

  // Show kebab menu when:
  // 1. canModify (not in read-only mode AND not read-only superuser) AND
  // 2. (Row is superuser AND viewing own row AND quota features enabled)
  //    OR (Row is NOT superuser)
  const shouldShowMenu =
    canModify &&
    (isRowSuperuser &&
    isCurrentUser &&
    quayConfig?.features?.QUOTA_MANAGEMENT &&
    quayConfig?.features?.EDIT_QUOTA
      ? true
      : !isRowSuperuser);

  // Early return if menu should not be shown (handles other superuser rows)
  if (props.isUser && !shouldShowMenu) {
    return null;
  }

  // If cannot modify, return null (no actions allowed)
  // This handles: read-only mode, read-only superuser, and non-superusers
  if (!canModify) {
    return null;
  }

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
      case 'Send Recovery E-mail':
        setIsSendRecoveryEmailModalOpen(true);
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
    // Add Configure Quota option (only for organizations, not users)
    ...(quayConfig?.features?.QUOTA_MANAGEMENT &&
    quayConfig?.features?.EDIT_QUOTA
      ? [
          <DropdownItem
            key="configureQuota"
            onClick={() => setIsConfigureQuotaModalOpen(true)}
            data-testid="configure-quota-option"
          >
            Configure Quota
          </DropdownItem>,
        ]
      : []),
  ];

  // Determine user menu items based on user type and viewing context
  const userMenuItems =
    isCurrentUser && isRowSuperuser
      ? [
          // Currently logged-in SUPERUSER viewing their own row
          // ONLY show Configure Quota (if features enabled)
          ...(quayConfig?.features?.QUOTA_MANAGEMENT &&
          quayConfig?.features?.EDIT_QUOTA
            ? [
                <DropdownItem
                  key="configureQuota"
                  onClick={() => setIsConfigureQuotaModalOpen(true)}
                  data-testid="configure-quota-option"
                >
                  Configure Quota
                </DropdownItem>,
              ]
            : []),
        ]
      : isRowSuperuser
      ? [] // Other superuser rows - no menu (already filtered by shouldShowMenu check above)
      : [
          // Regular user rows (not superusers)
          // Show user management options based on authentication type
          // Only show Change Email and Change Password for Database authentication
          ...(isDatabaseAuth
            ? [
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
              ]
            : []),
          // Add Send Recovery E-mail for regular users (only if MAILING feature enabled and Database auth)
          ...(quayConfig?.features?.MAILING && isDatabaseAuth
            ? [
                <DropdownItem
                  key="sendRecoveryEmail"
                  onClick={() => handleMenuItemClick('Send Recovery E-mail')}
                >
                  Send Recovery E-mail
                </DropdownItem>,
              ]
            : []),
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

          // Add Configure Quota for regular users
          ...(quayConfig?.features?.QUOTA_MANAGEMENT &&
          quayConfig?.features?.EDIT_QUOTA
            ? [
                <DropdownItem
                  key="configureQuota"
                  onClick={() => setIsConfigureQuotaModalOpen(true)}
                  data-testid="configure-quota-option"
                >
                  Configure Quota
                </DropdownItem>,
              ]
            : []),
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
      <SendRecoveryEmailModal
        isOpen={isSendRecoveryEmailModalOpen}
        onClose={() => setIsSendRecoveryEmailModalOpen(false)}
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

      {/* Configure Quota Modal - For both users and organizations */}
      {quayConfig?.features?.QUOTA_MANAGEMENT &&
        quayConfig?.features?.EDIT_QUOTA && (
          <ConfigureQuotaModal
            isOpen={isConfigureQuotaModalOpen}
            onClose={() => setIsConfigureQuotaModalOpen(false)}
            organizationName={props.name}
            isUser={props.isUser}
          />
        )}
    </>
  );
}

interface OrganizationOptionsKebabProps {
  name: string;
  isUser: boolean;
  userEnabled?: boolean; // Only used when isUser is true
  userSuperuser?: boolean; // Only used when isUser is true
}
