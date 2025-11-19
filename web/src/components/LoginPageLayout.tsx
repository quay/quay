import React, {useEffect} from 'react';
import {ListVariant, LoginPage} from '@patternfly/react-core';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {useLogo} from 'src/hooks/UseLogo';
import {useLoginFooterItems} from 'src/components/LoginFooter';
import SystemStatusBanner from 'src/components/SystemStatusBanner';
import {GlobalMessages} from 'src/components/GlobalMessages';
import './LoginPageLayout.css';

interface LoginPageLayoutProps {
  title: string;
  description: string;
  children: React.ReactNode;
  className?: string;
}

export function LoginPageLayout({
  title,
  description,
  children,
  className = 'pf-u-background-color-100 pf-v5-u-text-align-left',
}: LoginPageLayoutProps) {
  const quayConfig = useQuayConfig();
  const footerListItems = useLoginFooterItems();
  const logoUrl = useLogo();

  // Set document title from registry title
  useEffect(() => {
    if (quayConfig?.config?.REGISTRY_TITLE) {
      document.title = `${quayConfig.config.REGISTRY_TITLE} • Quay`;
    }
  }, [quayConfig]);

  return (
    <>
      <SystemStatusBanner />
      <GlobalMessages />
      <LoginPage
        className={className}
        brandImgSrc={logoUrl}
        brandImgAlt="Red Hat Quay"
        backgroundImgSrc="assets/images/rh_login.jpeg"
        textContent={description}
        loginTitle={title}
        footerListItems={footerListItems}
        footerListVariants={ListVariant.inline}
      >
        {children}
      </LoginPage>
    </>
  );
}
