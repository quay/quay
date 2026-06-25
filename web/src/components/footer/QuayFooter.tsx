import React from 'react';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {ServiceStatus} from './ServiceStatus';
import './QuayFooter.css';

export function QuayFooter() {
  const quayConfig = useQuayConfig();

  if (!quayConfig) {
    return null;
  }

  const footerItems: React.ReactNode[] = [];

  // Add branding footer image/link if configured
  if (quayConfig?.config?.BRANDING?.footer_img) {
    const imgElement = (
      <img src={quayConfig.config.BRANDING.footer_img} alt="Footer branding" />
    );

    footerItems.push(
      <li key="branding">
        {quayConfig.config.BRANDING.footer_url ? (
          <a
            href={quayConfig.config.BRANDING.footer_url}
            target="_blank"
            rel="noopener noreferrer"
          >
            {imgElement}
          </a>
        ) : (
          imgElement
        )}
      </li>,
    );
  }

  // Add Documentation link
  if (quayConfig?.config?.DOCUMENTATION_ROOT) {
    footerItems.push(
      <li key="docs">
        <a
          href={quayConfig.config.DOCUMENTATION_ROOT}
          target="_blank"
          rel="noopener noreferrer"
        >
          Documentation
        </a>
      </li>,
    );
  }

  // For quay.io and stage.quay.io with BILLING feature
  const isQuayIO =
    quayConfig?.config?.SERVER_HOSTNAME === 'quay.io' ||
    quayConfig?.config?.SERVER_HOSTNAME === 'stage.quay.io';

  if (isQuayIO && quayConfig?.features?.BILLING) {
    footerItems.push(
      <li key="terms">
        <a
          href="https://www.openshift.com/legal/terms"
          target="_blank"
          rel="noopener noreferrer"
        >
          Terms
        </a>
      </li>,
    );
    footerItems.push(
      <li key="privacy">
        <a
          href="https://www.redhat.com/en/about/privacy-policy"
          target="_blank"
          rel="noopener noreferrer"
        >
          Privacy
        </a>
      </li>,
    );
    footerItems.push(
      <li key="security">
        <a href="/security/" target="_self">
          Security
        </a>
      </li>,
    );
    footerItems.push(
      <li key="about">
        <a href="/about/" target="_self">
          About
        </a>
      </li>,
    );
    footerItems.push(
      <li key="trustarc">
        <span id="teconsent" style={{lineHeight: '1.1'}}></span>
      </li>,
    );
  } else {
    // For other deployments, use configurable footer links
    if (quayConfig?.config?.FOOTER_LINKS?.TERMS_OF_SERVICE_URL) {
      footerItems.push(
        <li key="terms">
          <a
            href={quayConfig.config.FOOTER_LINKS.TERMS_OF_SERVICE_URL}
            target="_blank"
            rel="noopener noreferrer"
          >
            Terms of Service
          </a>
        </li>,
      );
    }

    if (quayConfig?.config?.FOOTER_LINKS?.PRIVACY_POLICY_URL) {
      footerItems.push(
        <li key="privacy">
          <a
            href={quayConfig.config.FOOTER_LINKS.PRIVACY_POLICY_URL}
            target="_blank"
            rel="noopener noreferrer"
          >
            Privacy
          </a>
        </li>,
      );
    }

    if (quayConfig?.config?.FOOTER_LINKS?.SECURITY_URL) {
      footerItems.push(
        <li key="security">
          <a
            href={quayConfig.config.FOOTER_LINKS.SECURITY_URL}
            target="_blank"
            rel="noopener noreferrer"
          >
            Security
          </a>
        </li>,
      );
    }

    if (quayConfig?.config?.FOOTER_LINKS?.ABOUT_URL) {
      footerItems.push(
        <li key="about">
          <a
            href={quayConfig.config.FOOTER_LINKS.ABOUT_URL}
            target="_blank"
            rel="noopener noreferrer"
          >
            About
          </a>
        </li>,
      );
    }
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
      <li key="contact">
        <a href={contactHref} target="_self">
          Contact
        </a>
      </li>,
    );
  }

  // Add service status for quay.io with BILLING (independent of version)
  if (isQuayIO && quayConfig?.features?.BILLING) {
    footerItems.push(
      <li key="service-status">
        <ServiceStatus />
      </li>,
    );
  }

  // Don't render footer if there are no items and no version
  if (footerItems.length === 0 && !quayConfig?.version_number) {
    return null;
  }

  return (
    <>
      <nav id="quay-footer" className="quay-footer">
        <div className="quay-footer-container">
          <ul className="quay-footer-list">{footerItems}</ul>
          {quayConfig?.version_number && (
            <div className="quay-footer-version">
              {quayConfig.version_number}
            </div>
          )}
        </div>
      </nav>
      {isQuayIO && (
        <div
          id="consent_blackbar"
          style={{
            position: 'fixed',
            bottom: 0,
            width: '100%',
            zIndex: 5,
            padding: '10px',
          }}
        />
      )}
    </>
  );
}
