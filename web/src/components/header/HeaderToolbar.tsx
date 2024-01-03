import {
  Button,
  Divider,
  MenuGroup,
  MenuItem,
  MenuList,
  Flex,
  FlexItem,
  Icon,
  MenuContent,
  MenuToggle,
  Menu,
  Switch,
  ToggleGroup,
  ToggleGroupItem,
  Toolbar,
  ToolbarContent,
  ToolbarGroup,
  ToolbarItem,
  Tooltip,
  MenuContainer,
} from '@patternfly/react-core';
import {
  PowerOffIcon,
  UserIcon,
  WindowMaximizeIcon,
} from '@patternfly/react-icons';
import React, {useState} from 'react';
import {GlobalAuthState, logoutUser} from 'src/resources/AuthResource';
import {addDisplayError} from 'src/resources/ErrorHandling';
import ErrorModal from '../errors/ErrorModal';

import {useQueryClient} from '@tanstack/react-query';
import 'src/components/header/HeaderToolbar.css';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';

import MoonIcon from '@patternfly/react-icons/dist/esm/icons/moon-icon';
import SunIcon from '@patternfly/react-icons/dist/esm/icons/sun-icon';
import {ThemePreference, useTheme} from 'src/contexts/ThemeContext';

export function HeaderToolbar() {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const menuRef = React.useRef<HTMLDivElement>(null);
  const toggleRef = React.useRef<HTMLButtonElement>(null);
  const {themePreference, setThemePreference} = useTheme();

  const queryClient = useQueryClient();
  const {user} = useCurrentUser();
  const [err, setErr] = useState<string>();

  const onDropdownToggle = () => {
    setIsDropdownOpen((prev) => !prev);
  };

  const onMenuSelect = async (
    event: React.MouseEvent | undefined,
    itemId: string | number | undefined,
  ) => {
    switch (itemId) {
      case 'logout':
        try {
          await logoutUser();
          GlobalAuthState.csrfToken = undefined;
          queryClient.invalidateQueries(['user']);

          // Ignore client side auth page and use old UI if present
          // TODO: replace this with navigate('/signin') once new ui supports all auth methods
          const protocol = window.location.protocol;
          const host = window.location.host;
          window.location.replace(`${protocol}//${host}/signin/`);
        } catch (err) {
          console.error(err);
          setErr(addDisplayError('Unable to log out', err));
        }
        setIsDropdownOpen(false);
        break;
      case 'theme-selector':
        break;
      default:
        setIsDropdownOpen(false);
        break;
    }
  };

  const userMenu = (
    <Menu ref={menuRef} onSelect={onMenuSelect}>
      <MenuContent>
        <MenuGroup label="Appearance" key="theme">
          <MenuList>
            <MenuItem
              itemId="theme-selector"
              key="theme-selector"
              component="object"
            >
              <ToggleGroup id="theme-toggle" aria-label="Theme toggle group">
                <ToggleGroupItem
                  icon={
                    <Icon size="sm">
                      <SunIcon />
                    </Icon>
                  }
                  aria-label="light theme"
                  aria-describedby="tooltip-auto-theme"
                  buttonId="toggle-group-light-theme"
                  onChange={() => {
                    if (themePreference !== ThemePreference.LIGHT) {
                      setThemePreference(ThemePreference.LIGHT);
                    }
                  }}
                  isSelected={themePreference === ThemePreference.LIGHT}
                />
                <ToggleGroupItem
                  icon={
                    <Icon size="sm">
                      <MoonIcon />
                    </Icon>
                  }
                  aria-label="dark theme"
                  buttonId="toggle-group-dark-theme"
                  onChange={() => {
                    if (themePreference !== ThemePreference.DARK) {
                      setThemePreference(ThemePreference.DARK);
                    }
                  }}
                  isSelected={themePreference === ThemePreference.DARK}
                />
                <ToggleGroupItem
                  icon={
                    <Icon size="sm">
                      <WindowMaximizeIcon />
                    </Icon>
                  }
                  aria-label="auto theme"
                  buttonId="toggle-group-auto-theme"
                  onChange={() => {
                    if (themePreference !== ThemePreference.AUTO) {
                      setThemePreference(ThemePreference.AUTO);
                    }
                  }}
                  isSelected={themePreference === ThemePreference.AUTO}
                />
              </ToggleGroup>
            </MenuItem>
          </MenuList>
        </MenuGroup>
        <Divider />
        <MenuGroup label="Actions" key="user">
          <MenuList>
            <MenuItem
              icon={<PowerOffIcon aria-hidden />}
              isDanger={true}
              itemId="logout"
              key="logout"
              component="button"
            >
              Logout
            </MenuItem>
          </MenuList>
        </MenuGroup>
        <Tooltip
          id="tooltip-light-theme"
          content="Light theme"
          position="bottom"
          triggerRef={() =>
            document.getElementById(
              'toggle-group-light-theme',
            ) as HTMLButtonElement
          }
        />
        <Tooltip
          id="tooltip-dark-theme"
          content="Dark theme"
          position="bottom"
          triggerRef={() =>
            document.getElementById(
              'toggle-group-dark-theme',
            ) as HTMLButtonElement
          }
        />
        <Tooltip
          id="tooltip-auto-theme"
          content="Device-based theme"
          position="bottom"
          triggerRef={() =>
            document.getElementById(
              'toggle-group-auto-theme',
            ) as HTMLButtonElement
          }
        />
      </MenuContent>
    </Menu>
  );

  const toggle = (
    <MenuToggle
      ref={toggleRef}
      onClick={onDropdownToggle}
      isExpanded={isDropdownOpen}
      icon={<UserIcon />}
      id="user-menu-toggle"
      aria-label="User menu"
    >
      {user.username}
    </MenuToggle>
  );

  const menuContainer = (
    <MenuContainer
      menu={userMenu}
      menuRef={menuRef}
      isOpen={isDropdownOpen}
      toggle={toggle}
      toggleRef={toggleRef}
      onOpenChange={(isOpen) => setIsDropdownOpen(isOpen)}
    />
  );

  const signInButton = <Button> Sign In </Button>;

  // Toggle between old UI and new UI
  const [isChecked, setIsChecked] = React.useState<boolean>(true);
  const toggleSwitch = (
    _event: React.FormEvent<HTMLInputElement>,
    checked: boolean,
  ) => {
    setIsChecked(checked);

    // Reload page and trigger patternfly cookie removal
    const protocol = window.location.protocol;
    const host = window.location.host;
    const path = 'angular';

    // Add a random arg so nginx redirect to / doesn't get cached by browser
    const randomArg = '?_=' + new Date().getTime();
    window.location.replace(`${protocol}//${host}/${path}/${randomArg}`);
  };

  return (
    <>
      <ErrorModal error={err} setError={setErr} />
      <Toolbar id="toolbar" isFullHeight isStatic>
        <ToolbarContent>
          <ToolbarGroup
            variant="icon-button-group"
            align={{default: 'alignRight'}}
            spacer={{default: 'spacerNone', md: 'spacerMd'}}
          >
            <ToolbarItem
              spacer={{
                default: 'spacerNone',
                md: 'spacerSm',
                lg: 'spacerMd',
                xl: 'spacerLg',
              }}
            >
              <Flex
                spaceItems={{default: 'spaceItemsMd'}}
                flexWrap={{default: 'nowrap'}}
                className="pf-v5-u-text-nowrap pf-v5-u-pr-md"
              >
                <FlexItem alignSelf={{default: 'alignSelfFlexStart'}}>
                  Current UI
                </FlexItem>
                <Switch
                  id="header-toolbar-ui-switch"
                  label="New UI"
                  labelOff="New UI"
                  isChecked={isChecked}
                  onChange={toggleSwitch}
                />
              </Flex>
            </ToolbarItem>
            <ToolbarItem>
              {user.username ? menuContainer : signInButton}
            </ToolbarItem>
          </ToolbarGroup>
        </ToolbarContent>
      </Toolbar>
    </>
  );
}
