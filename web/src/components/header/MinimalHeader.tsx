import {
  Masthead,
  MastheadMain,
  MastheadLogo,
  MastheadBrand,
  Brand,
} from '@patternfly/react-core';
import {Link} from 'react-router-dom';
import {useLogo} from 'src/hooks/UseLogo';
import './QuayHeader.css';

export function MinimalHeader() {
  const logoUrl = useLogo();

  return (
    <Masthead data-testid="minimal-header">
      <MastheadMain>
        <MastheadBrand>
          <MastheadLogo component={(props) => <Link {...props} to="/signin" />}>
            <Brand src={logoUrl} alt="Red Hat Quay" className={'header-logo'} />
          </MastheadLogo>
        </MastheadBrand>
      </MastheadMain>
    </Masthead>
  );
}
