import React from 'react';
import {Control, FieldErrors, useWatch} from 'react-hook-form';
import {
  Divider,
  Title,
  HelperText,
  HelperTextItem,
} from '@patternfly/react-core';
import {FormTextInput} from 'src/components/forms/FormTextInput';
import {OrgMirrorConfig} from 'src/resources/OrgMirrorResource';
import {OrgMirroringFormData} from './types';

interface OrgMirroringCredentialsProps {
  control: Control<OrgMirroringFormData>;
  errors: FieldErrors<OrgMirroringFormData>;
  config: OrgMirrorConfig | null;
}

export const OrgMirroringCredentials: React.FC<
  OrgMirroringCredentialsProps
> = ({control, errors, config}) => {
  const username = useWatch({control, name: 'username'});
  const externalRegistryType = useWatch({
    control,
    name: 'externalRegistryType',
  });
  const isQuay = externalRegistryType === 'quay';

  return (
    <>
      <Divider />
      <Title headingLevel="h3">Credentials</Title>
      <HelperText>
        <HelperTextItem>
          Required if the source registry requires authentication.
        </HelperTextItem>
      </HelperText>

      <FormTextInput
        name="username"
        control={control}
        errors={errors}
        label="Username"
        fieldId="username"
        placeholder={isQuay ? '$oauthtoken' : undefined}
        showNoneWhenEmpty={!!config}
        data-testid="username-input"
      />

      <FormTextInput
        name="password"
        control={control}
        errors={errors}
        label="Password"
        fieldId="external_registry_password"
        type="password"
        placeholder={
          config?.has_external_registry_password
            ? '••••••••  (leave blank to keep current)'
            : undefined
        }
        showNoneWhenEmpty={!!config && !config.has_external_registry_password}
        customValidation={(value: string) =>
          value && !isQuay && !username?.trim()
            ? 'Username is required when setting a password'
            : true
        }
        data-testid="password-input"
      />
    </>
  );
};
