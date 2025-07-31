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

export default function OrganizationOptionsKebab(
  props: OrganizationOptionsKebabProps,
) {
  const [isKebabOpen, setIsKebabOpen] = useState<boolean>(false);

  const handleMenuItemClick = (action: string) => {
    console.log(
      `${action} clicked for ${props.isUser ? 'user' : 'organization'}: ${
        props.name
      }`,
    );
    setIsKebabOpen(false);
    // TODO: Implement actual actions
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
  );
}

interface OrganizationOptionsKebabProps {
  name: string;
  isUser: boolean;
}
