import {
  Masthead,
  MastheadMain,
  MastheadBrand,
  Brand,
} from '@patternfly/react-core';
import logo from 'src/assets/quay.svg';
import rh_logo from 'src/assets/RH_QuayIO2.svg';
import {Link} from 'react-router-dom';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import axios from 'src/libs/axios';
import './QuayHeader.css';

export function MinimalHeader() {
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

  return (
    <Masthead data-testid="minimal-header">
      <MastheadMain>
        <MastheadBrand component={(props) => <Link {...props} to="/signin" />}>
          <Brand src={logoUrl} alt="Red Hat Quay" className={'header-logo'} />
        </MastheadBrand>
      </MastheadMain>
    </Masthead>
  );
}
