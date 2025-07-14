import React from 'react';
import {Controller, Control, FieldValues, Path} from 'react-hook-form';
import {FormGroup, Checkbox} from '@patternfly/react-core';

interface FormCheckboxProps<T extends FieldValues> {
  name: Path<T>;
  control: Control<T>;
  label: string;
  fieldId?: string;
  description?: string;
  isStack?: boolean;
  'data-testid'?: string;
  customOnChange?: (
    checked: boolean,
    onChange: (value: boolean) => void,
  ) => void;
}

export function FormCheckbox<T extends FieldValues>({
  name,
  control,
  label,
  fieldId,
  description,
  isStack = true,
  'data-testid': dataTestId,
  customOnChange,
}: FormCheckboxProps<T>) {
  return (
    <FormGroup fieldId={fieldId || name} isStack={isStack}>
      <Controller
        name={name}
        control={control}
        render={({field: {value, onChange}}) => (
          <Checkbox
            label={label}
            id={fieldId || name}
            description={description}
            isChecked={value}
            onChange={(_event, checked) => {
              if (customOnChange) {
                customOnChange(checked, onChange);
              } else {
                onChange(checked);
              }
            }}
            data-testid={dataTestId}
          />
        )}
      />
    </FormGroup>
  );
}
