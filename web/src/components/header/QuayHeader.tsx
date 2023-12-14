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
import {HeaderToolbar} from './HeaderToolbar';
import {Link} from 'react-router-dom';
import {SidebarState} from 'src/atoms/SidebarState';
import {useRecoilState} from 'recoil';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import './QuayHeader.css';
import {fetchBrandLogo} from 'src/libs/utils';

export function QuayHeader() {
  const [_sidebarState, setSidebarState] = useRecoilState(SidebarState);
  const quayConfig = useQuayConfig();

  const fetchLogoUrl = () => {
    if (
      quayConfig &&
      quayConfig.config?.BRANDING &&
      quayConfig.config.BRANDING?.footer_url
    ) {
      return `${quayConfig.config.BRANDING.footer_url}`;
    }

    return '/';
  };

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
        <MastheadBrand
          component={(props) => <Link {...props} to={fetchLogoUrl()} />}
        >
          <Brand
            src={fetchBrandLogo(quayConfig)}
            alt="Red Hat Quay"
            className={'header-logo'}
          />
        </MastheadBrand>
      </MastheadMain>
      <MastheadContent>
        <HeaderToolbar />
      </MastheadContent>
    </Masthead>
  );
}
