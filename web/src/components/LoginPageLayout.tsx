import React, {useEffect} from 'react';
import {ListVariant, LoginPage} from '@patternfly/react-core';
import logo from 'src/assets/quay.svg';
import axios from 'src/libs/axios';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {useLoginFooterItems} from 'src/components/LoginFooter';
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

  // Determine logo URL from config
  let logoUrl = logo;
  if (quayConfig && quayConfig.config?.ENTERPRISE_DARK_LOGO_URL) {
    logoUrl = `${axios.defaults.baseURL}${quayConfig.config.ENTERPRISE_DARK_LOGO_URL}`;
  }

  // Set document title from registry title
  useEffect(() => {
    if (quayConfig?.config?.REGISTRY_TITLE) {
      document.title = `${quayConfig.config.REGISTRY_TITLE} • Quay`;
    }
  }, [quayConfig]);

  return (
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
  );
}
