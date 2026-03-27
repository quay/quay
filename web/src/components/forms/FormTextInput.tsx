import React from 'react';
import {
  Controller,
  Control,
  FieldErrors,
  FieldValues,
  Path,
} from 'react-hook-form';
import {
  FormGroup,
  FormHelperText,
  TextInput,
  Content,
  ValidatedOptions,
} from '@patternfly/react-core';

interface FormTextInputProps<T extends FieldValues> {
  name: Path<T>;
  control: Control<T>;
  errors: FieldErrors<T>;
  label: string;
  fieldId?: string;
  placeholder?: string;
  type?: 'text' | 'password' | 'email' | 'datetime-local';
  required?: boolean;
  customValidation?: (value: string) => string | boolean;
  helperText?: string;
  isStack?: boolean;
  'data-testid'?: string;
  pattern?: string;
  inputMode?:
    | 'none'
    | 'text'
    | 'tel'
    | 'url'
    | 'email'
    | 'numeric'
    | 'decimal'
    | 'search';
  'aria-label'?: string;
  showNoneWhenEmpty?: boolean;
  disabled?: boolean;
}

export function FormTextInput<T extends FieldValues>({
  name,
  control,
  errors,
  label,
  fieldId,
  placeholder,
  type = 'text',
  required = false,
  customValidation,
  helperText,
  isStack = true,
  'data-testid': dataTestId,
  pattern,
  inputMode,
  'aria-label': ariaLabel,
  showNoneWhenEmpty = false,
  disabled = false,
}: FormTextInputProps<T>) {
  const rules = {
    ...(required && {
      required: 'This field is required',
      validate: (value: string) =>
        value?.trim() !== '' || 'This field is required',
    }),
    ...(customValidation && {
      validate: customValidation,
    }),
  };

  const fieldError = errors[name];
  const validationState = fieldError
    ? ValidatedOptions.error
    : ValidatedOptions.default;

  return (
    <FormGroup
      label={label}
      fieldId={fieldId || name}
      isStack={isStack}
      isRequired={required}
    >
      <Controller
        name={name}
        control={control}
        rules={rules}
        render={({field: {value, onChange}}) => {
          const displayValue =
            showNoneWhenEmpty && (!value || value === '')
              ? 'None'
              : value || '';
          const handleChange = (
            _event: React.FormEvent<HTMLInputElement>,
            newValue: string,
          ) => {
            if (showNoneWhenEmpty && newValue === 'None') {
              onChange('');
            } else {
              onChange(newValue);
            }
          };

          return (
            <>
              <TextInput
                type={type}
                id={fieldId || name}
                placeholder={placeholder}
                value={displayValue}
                onChange={handleChange}
                validated={validationState}
                data-testid={dataTestId}
                pattern={pattern}
                inputMode={inputMode}
                aria-label={ariaLabel}
                isDisabled={disabled}
              />
              {fieldError && (
                <FormHelperText>
                  <Content component="p" className="pf-m-error">
                    {fieldError.message as string}
                  </Content>
                </FormHelperText>
              )}
              {helperText && !fieldError && (
                <FormHelperText>
                  <Content component="p">{helperText}</Content>
                </FormHelperText>
              )}
            </>
          );
        }}
      />
    </FormGroup>
  );
}
