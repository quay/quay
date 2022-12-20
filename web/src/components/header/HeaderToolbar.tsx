import {
  Button,
  Dropdown,
  DropdownGroup,
  DropdownItem,
  DropdownToggle,
  Form,
  FormGroup,
  Switch,
  Toolbar,
  ToolbarContent,
  ToolbarGroup,
  ToolbarItem,
} from '@patternfly/react-core';
import {UserIcon} from '@patternfly/react-icons';
import React from 'react';
import {useState} from 'react';
import {GlobalAuthState, logoutUser} from 'src/resources/AuthResource';
import {addDisplayError} from 'src/resources/ErrorHandling';
import ErrorModal from '../errors/ErrorModal';

import 'src/components/header/HeaderToolbar.css';
import {useQueryClient} from '@tanstack/react-query';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';

export function HeaderToolbar() {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);

  const queryClient = useQueryClient();
  const {user} = useCurrentUser();
  const [err, setErr] = useState<string>();

  const onDropdownToggle = () => {
    setIsDropdownOpen((prev) => !prev);
  };

  const onDropdownSelect = async (e) => {
    setIsDropdownOpen(false);
    switch (e.target.value) {
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
        break;
      default:
        break;
    }
  };

  const userDropdownItems = [
    <DropdownGroup key="group 2">
      <DropdownItem value="logout" key="group 2 logout" component="button">
        Logout
      </DropdownItem>
    </DropdownGroup>,
  ];

  const userDropdown = (
    <Dropdown
      position="right"
      onSelect={(value) => onDropdownSelect(value)}
      isOpen={isDropdownOpen}
      toggle={
        <DropdownToggle icon={<UserIcon />} onToggle={onDropdownToggle}>
          {user.username}
        </DropdownToggle>
      }
      dropdownItems={userDropdownItems}
    />
  );

  const signInButton = <Button> Sign In </Button>;

  // Toggle between old UI and new UI
  const [isChecked, setIsChecked] = React.useState<boolean>(true);
  const toggleSwitch = (checked: boolean) => {
    setIsChecked(checked);

    // Reload page and trigger patternfly cookie removal
    const protocol = window.location.protocol;
    const host = window.location.host;
    const path = 'angular';

    // Add a random arg so nginx redirect to / doesn't get cached by browser
    const randomArg = '?_=' + new Date().getTime();
    window.location.replace(`${protocol}//${host}/${path}/${randomArg}`);
  };
  const toolbarSpacers = {
    default: 'spacerNone',
    md: 'spacerSm',
    lg: 'spacerMd',
    xl: 'spacerLg',
  };

  return (
    <>
      <ErrorModal error={err} setError={setErr} />
      <Toolbar id="toolbar" isFullHeight isStatic>
        <ToolbarContent>
          <ToolbarGroup
            variant="icon-button-group"
            alignment={{default: 'alignRight'}}
            spacer={{default: 'spacerNone', md: 'spacerMd'}}
          >
            <ToolbarItem spacer={toolbarSpacers}>
              <Form isHorizontal>
                <FormGroup
                  label="Current UI"
                  fieldId="horizontal-form-stacked-options"
                >
                  <Switch
                    id="header-toolbar-ui-switch"
                    label="New UI"
                    labelOff="New UI"
                    isChecked={isChecked}
                    onChange={toggleSwitch}
                  />
                </FormGroup>
              </Form>
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
