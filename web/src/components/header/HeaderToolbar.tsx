import React, {useState} from 'react';
import {
  Button,
  Dropdown,
  DropdownItem,
  DropdownList,
  Flex,
  FlexItem,
  MenuToggle,
  MenuToggleElement,
  Switch,
  Toolbar,
  ToolbarContent,
  ToolbarGroup,
  ToolbarItem,
} from '@patternfly/react-core';
import {UserIcon} from '@patternfly/react-icons';
import {GlobalAuthState, logoutUser} from 'src/resources/AuthResource';
import {addDisplayError} from 'src/resources/ErrorHandling';
import ErrorModal from '../errors/ErrorModal';

import 'src/components/header/HeaderToolbar.css';
import {useQueryClient} from '@tanstack/react-query';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
import {useLocation, useNavigate} from 'react-router-dom';
import {getSignInPath} from 'src/routes/NavigationPath';

export function HeaderToolbar() {
  const location = useLocation();
  const navigate = useNavigate();
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);

  const queryClient = useQueryClient();
  const {user} = useCurrentUser();
  const [err, setErr] = useState<string>();

  const onDropdownToggle = () => {
    setIsDropdownOpen((prev) => !prev);
  };

  const onDropdownSelect = async (value) => {
    setIsDropdownOpen(false);
    switch (value) {
      case 'logout':
        try {
          await logoutUser();
          GlobalAuthState.csrfToken = undefined;
          queryClient.invalidateQueries(['user']);

          navigate(getSignInPath(location.pathname));
        } catch (err) {
          console.error(err);
          setErr(addDisplayError('Unable to log out', err));
        }
        break;
      default:
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
      </DropdownList>
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
