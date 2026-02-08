import React, {useState} from 'react';
import {Control, FieldErrors, Controller} from 'react-hook-form';
import {
  FormGroup,
  Select,
  SelectOption,
  MenuToggle,
  Radio,
} from '@patternfly/react-core';
import {FormTextInput} from 'src/components/forms/FormTextInput';
import {OrgMirroringFormData} from './types';

interface OrgMirroringSourceProps {
  control: Control<OrgMirroringFormData>;
  errors: FieldErrors<OrgMirroringFormData>;
}

export const OrgMirroringSource: React.FC<OrgMirroringSourceProps> = ({
  control,
  errors,
}) => {
  const [isTypeSelectOpen, setIsTypeSelectOpen] = useState(false);

  const registryTypeLabels: Record<string, string> = {
    harbor: 'Harbor',
    quay: 'Quay',
  };

  return (
    <>
      <FormGroup
        label="Source Registry Type"
        fieldId="external_registry_type"
        isStack
        isRequired
      >
        <Controller
          name="externalRegistryType"
          control={control}
          rules={{required: 'This field is required'}}
          render={({field: {value, onChange}}) => (
            <Select
              isOpen={isTypeSelectOpen}
              onOpenChange={(isOpen) => setIsTypeSelectOpen(isOpen)}
              onSelect={(_event, selectedValue) => {
                onChange(selectedValue as string);
                setIsTypeSelectOpen(false);
              }}
              selected={value}
              aria-label="Source registry type"
              toggle={(toggleRef) => (
                <MenuToggle
                  ref={toggleRef}
                  onClick={() => setIsTypeSelectOpen(!isTypeSelectOpen)}
                  isExpanded={isTypeSelectOpen}
                  data-testid="registry-type-toggle"
                >
                  {registryTypeLabels[value] || value}
                </MenuToggle>
              )}
            >
              <SelectOption value="harbor">Harbor</SelectOption>
              <SelectOption value="quay">Quay</SelectOption>
            </Select>
          )}
        />
      </FormGroup>

      <FormTextInput
        name="externalRegistryUrl"
        control={control}
        errors={errors}
        label="Source Registry URL"
        fieldId="external_registry_url"
        placeholder="https://registry.example.com"
        required
        data-testid="registry-url-input"
      />

      <FormTextInput
        name="externalNamespace"
        control={control}
        errors={errors}
        label="Source Namespace"
        fieldId="external_namespace"
        placeholder="my-project"
        required
        helperText="The namespace or project name on the source registry."
        data-testid="namespace-input"
      />

      <FormGroup
        label="Repository Visibility"
        fieldId="visibility"
        isStack
        isRequired
      >
        <Controller
          name="visibility"
          control={control}
          rules={{required: 'Select visibility'}}
          render={({field: {value, onChange}}) => (
            <>
              <Radio
                isChecked={value === 'private'}
                name="visibility"
                onChange={() => onChange('private')}
                label="Private"
                id="visibility-private"
                description="Created repositories will be private."
                data-testid="visibility-private"
              />
              <Radio
                isChecked={value === 'public'}
                name="visibility"
                onChange={() => onChange('public')}
                label="Public"
                id="visibility-public"
                description="Created repositories will be publicly accessible."
                data-testid="visibility-public"
              />
            </>
          )}
        />
      </FormGroup>
    </>
  );
};
