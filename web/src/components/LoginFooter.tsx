import React from 'react';
import {ListItem} from '@patternfly/react-core';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';

export function useLoginFooterItems() {
  const quayConfig = useQuayConfig();

  const footerItems: React.ReactNode[] = [];

  if (quayConfig?.config?.FOOTER_LINKS?.TERMS_OF_SERVICE_URL) {
    footerItems.push(
      <ListItem key="terms">
        <a
          href={quayConfig.config.FOOTER_LINKS.TERMS_OF_SERVICE_URL}
          target="_blank"
          rel="noopener noreferrer"
        >
          Terms of Service
        </a>
      </ListItem>,
    );
  }

  if (quayConfig?.config?.FOOTER_LINKS?.PRIVACY_POLICY_URL) {
    footerItems.push(
      <ListItem key="privacy">
        <a
          href={quayConfig.config.FOOTER_LINKS.PRIVACY_POLICY_URL}
          target="_blank"
          rel="noopener noreferrer"
        >
          Privacy
        </a>
      </ListItem>,
    );
  }

  if (quayConfig?.config?.FOOTER_LINKS?.SECURITY_URL) {
    footerItems.push(
      <ListItem key="security">
        <a
          href={quayConfig.config.FOOTER_LINKS.SECURITY_URL}
          target="_blank"
          rel="noopener noreferrer"
        >
          Security
        </a>
      </ListItem>,
    );
  }

  if (quayConfig?.config?.FOOTER_LINKS?.ABOUT_URL) {
    footerItems.push(
      <ListItem key="about">
        <a
          href={quayConfig.config.FOOTER_LINKS.ABOUT_URL}
          target="_blank"
          rel="noopener noreferrer"
        >
          About
        </a>
      </ListItem>,
    );
  }

  if (quayConfig?.config?.DOCUMENTATION_ROOT) {
    footerItems.push(
      <ListItem key="docs">
        <a
          href={quayConfig.config.DOCUMENTATION_ROOT}
          target="_blank"
          rel="noopener noreferrer"
        >
          Documentation
        </a>
      </ListItem>,
    );
  }

  // Add Contact link if configured
  const hasContact =
    quayConfig?.config?.CONTACT_INFO &&
    quayConfig.config.CONTACT_INFO.length > 0;
  if (hasContact) {
    const contactHref =
      quayConfig.config.CONTACT_INFO.length === 1
        ? quayConfig.config.CONTACT_INFO[0]
        : '/contact/';
    footerItems.push(
      <ListItem key="contact">
        <a href={contactHref} target="_self">
          Contact
        </a>
      </ListItem>,
    );
  }

  return footerItems.length > 0 ? footerItems : null;
}
