import React from 'react';
import {Control, FieldErrors} from 'react-hook-form';
import {Divider, Title} from '@patternfly/react-core';
import {FormTextInput} from 'src/components/forms/FormTextInput';
import {FormCheckbox} from 'src/components/forms/FormCheckbox';
import {OrgMirrorConfig} from 'src/resources/OrgMirrorResource';
import {OrgMirroringFormData} from './types';

interface OrgMirroringAdvancedSettingsProps {
  control: Control<OrgMirroringFormData>;
  errors: FieldErrors<OrgMirroringFormData>;
  config: OrgMirrorConfig | null;
}

export const OrgMirroringAdvancedSettings: React.FC<
  OrgMirroringAdvancedSettingsProps
> = ({control, errors, config}) => {
  return (
    <>
      <Divider />
      <Title headingLevel="h3">Advanced Settings</Title>

      <FormCheckbox
        name="verifyTls"
        control={control}
        label="Verify TLS"
        fieldId="verify_tls"
        description="Require HTTPS and verify certificates when talking to the source registry."
        data-testid="verify-tls-checkbox"
      />

      <FormTextInput
        name="httpProxy"
        control={control}
        errors={errors}
        label="HTTP Proxy"
        fieldId="http_proxy"
        placeholder="proxy.example.com"
        showNoneWhenEmpty={!!config}
        data-testid="http-proxy-input"
      />

      <FormTextInput
        name="httpsProxy"
        control={control}
        errors={errors}
        label="HTTPS Proxy"
        fieldId="https_proxy"
        placeholder="proxy.example.com"
        showNoneWhenEmpty={!!config}
        data-testid="https-proxy-input"
      />

      <FormTextInput
        name="noProxy"
        control={control}
        errors={errors}
        label="No Proxy"
        fieldId="no_proxy"
        placeholder="example.com"
        showNoneWhenEmpty={!!config}
        data-testid="no-proxy-input"
      />
    </>
  );
};
