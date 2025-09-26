import React from 'react';
import ReCAPTCHA from 'react-google-recaptcha';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';

interface ReCaptchaProps {
  onChange: (token: string | null) => void;
  className?: string;
}

export function ReCaptcha({onChange, className}: ReCaptchaProps) {
  const config = useQuayConfig();

  if (!config?.features?.RECAPTCHA || !config?.config?.RECAPTCHA_SITE_KEY) {
    return null;
  }

  return (
    <div className={className}>
      <ReCAPTCHA
        sitekey={config.config.RECAPTCHA_SITE_KEY}
        onChange={onChange}
      />
    </div>
  );
}
