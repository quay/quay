import React from 'react';
import {Control, FieldErrors} from 'react-hook-form';
import {Divider, Text, Title} from '@patternfly/react-core';
import {FormTextInput} from 'src/components/forms/FormTextInput';
import {MirroringConfigResponse} from 'src/resources/MirroringResource';
import {MirroringFormData} from './types';

interface MirroringCredentialsProps {
  control: Control<MirroringFormData>;
  errors: FieldErrors<MirroringFormData>;
  config: MirroringConfigResponse | null;
}

export const MirroringCredentials: React.FC<MirroringCredentialsProps> = ({
  control,
  errors,
  config,
}) => {
  return (
    <>
      <Divider />
      <Title headingLevel="h3">Credentials</Title>
      <Text
        component="small"
        className="pf-v5-c-form__helper-text pf-v5-u-text-align-center pf-v5-u-display-block"
      >
        Required if the external repository is private.
      </Text>

      <FormTextInput
        name="username"
        control={control}
        errors={errors}
        label="Username"
        fieldId="username"
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
        showNoneWhenEmpty={!!config}
        data-testid="password-input"
      />
    </>
  );
};
