import {
  Button,
  Dropdown,
  DropdownItem,
  DropdownList,
  Flex,
  FlexItem,
  Icon,
  MenuToggle,
  MenuToggleElement,
  Switch,
  ToggleGroup,
  ToggleGroupItem,
  Toolbar,
  ToolbarContent,
  ToolbarGroup,
  ToolbarItem,
  Tooltip,
} from '@patternfly/react-core';
import {UserIcon, WindowMaximizeIcon} from '@patternfly/react-icons';
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
  const {themePreference, setThemePreference} = useTheme();

  const queryClient = useQueryClient();
  const {user} = useCurrentUser();
  const [err, setErr] = useState<string>();

  const onDropdownToggle = () => {
    setIsDropdownOpen((prev) => !prev);
  };

  const onDropdownSelect = async (value) => {
    switch (value) {
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

  const userDropdown = (
    <Dropdown
      onSelect={(_event, value) => onDropdownSelect(value)}
      isOpen={isDropdownOpen}
      toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
        <MenuToggle
          ref={toggleRef}
          onClick={onDropdownToggle}
          isExpanded={isDropdownOpen}
          icon={<UserIcon />}
        >
          {user.username}
        </MenuToggle>
      )}
      onOpenChange={(isOpen) => setIsDropdownOpen(isOpen)}
      shouldFocusToggleOnSelect
    >
      <DropdownList>
        <DropdownItem value="logout" key="logout" component="button">
          Logout
        </DropdownItem>
        <DropdownItem
          value="theme-selector"
          key="theme-selector"
          component="object"
        >
          <ToggleGroup aria-label="Theme toggle group">
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
        </DropdownItem>
      </DropdownList>
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
        content="Browser-based theme"
        position="bottom"
        triggerRef={() =>
          document.getElementById(
            'toggle-group-auto-theme',
          ) as HTMLButtonElement
        }
      />
    </Dropdown>
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
              {user.username ? userDropdown : signInButton}
            </ToolbarItem>
          </ToolbarGroup>
        </ToolbarContent>
      </Toolbar>
    </>
  );
}
