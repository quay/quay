import React from 'react';

import {
  Masthead,
  MastheadToggle,
  MastheadMain,
  MastheadBrand,
  Button,
  MastheadContent,
  Brand,
} from '@patternfly/react-core';

import BarsIcon from '@patternfly/react-icons/dist/js/icons/bars-icon';
import logo from 'src/assets/quay.svg';
import rh_logo from 'src/assets/RH_QuayIO2.svg';
import {HeaderToolbar} from './HeaderToolbar';
import {Link} from 'react-router-dom';
import {SidebarState} from 'src/atoms/SidebarState';
import {useRecoilState} from 'recoil';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import axios from 'src/libs/axios';
import './QuayHeader.css';

export function QuayHeader() {
  const [_sidebarState, setSidebarState] = useRecoilState(SidebarState);
  const quayConfig = useQuayConfig();
  let logoUrl = logo;
  if (quayConfig && quayConfig.config?.ENTERPRISE_DARK_LOGO_URL) {
    logoUrl = `${axios.defaults.baseURL}${quayConfig.config.ENTERPRISE_DARK_LOGO_URL}`;
  } else if (
    window?.location?.hostname === 'stage.quay.io' ||
    window?.location?.hostname === 'quay.io'
  ) {
    logoUrl = rh_logo;
  }

  const toggleSidebarVisibility = () => {
    setSidebarState((oldState) => ({isOpen: !oldState.isOpen}));
  };

  return (
    <Masthead>
      <MastheadToggle>
        <Button
          variant="plain"
          aria-label="Global navigation"
          onClick={toggleSidebarVisibility}
        >
          <BarsIcon />
        </Button>
      </MastheadToggle>
      <MastheadMain>
        <MastheadBrand component={(props) => <Link {...props} to="/" />}>
          <Brand src={logoUrl} alt="Red Hat Quay" className={'header-logo'} />
        </MastheadBrand>
      </MastheadMain>
      <MastheadContent>
        <HeaderToolbar />
      </MastheadContent>
    </Masthead>
  );
}
