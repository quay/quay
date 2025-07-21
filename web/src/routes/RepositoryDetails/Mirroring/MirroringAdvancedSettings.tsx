import React from 'react';
import {Control, FieldErrors} from 'react-hook-form';
import {Divider, Title} from '@patternfly/react-core';
import {FormTextInput} from 'src/components/forms/FormTextInput';
import {FormCheckbox} from 'src/components/forms/FormCheckbox';
import {MirroringConfigResponse} from 'src/resources/MirroringResource';
import {MirroringFormData} from './types';

interface MirroringAdvancedSettingsProps {
  control: Control<MirroringFormData>;
  errors: FieldErrors<MirroringFormData>;
  config: MirroringConfigResponse | null;
}

export const MirroringAdvancedSettings: React.FC<
  MirroringAdvancedSettingsProps
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
        description="Require HTTPS and verify certificates when talking to the external registry."
        data-testid="verify-tls-checkbox"
      />

      <FormCheckbox
        name="unsignedImages"
        control={control}
        label="Accept Unsigned Images"
        fieldId="unsigned_images"
        description="Allow unsigned images to be mirrored."
        data-testid="unsigned-images-checkbox"
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
        label="HTTPs Proxy"
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
