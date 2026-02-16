import React, {useState} from 'react';
import {Control, FieldErrors, Controller} from 'react-hook-form';
import {
  FormGroup,
  HelperText,
  HelperTextItem,
  TextInput,
  Button,
  InputGroup,
  InputGroupText,
  Select,
  SelectOption,
  MenuToggle,
  ValidatedOptions,
  Split,
  SplitItem,
} from '@patternfly/react-core';
import {FormTextInput} from 'src/components/forms/FormTextInput';
import {OrgMirrorConfig} from 'src/resources/OrgMirrorResource';
import {OrgMirroringFormData} from './types';

interface OrgMirroringSyncScheduleProps {
  control: Control<OrgMirroringFormData>;
  errors: FieldErrors<OrgMirroringFormData>;
  config: OrgMirrorConfig | null;
  isSyncingNow: boolean;
  onSyncNow: () => Promise<void>;
}

export const OrgMirroringSyncSchedule: React.FC<
  OrgMirroringSyncScheduleProps
> = ({control, errors, config, isSyncingNow, onSyncNow}) => {
  const [isSyncUnitOpen, setIsSyncUnitOpen] = useState(false);

  return (
    <>
      <FormGroup
        label={config ? 'Next Sync Date' : 'Start Date'}
        fieldId="sync_start_date"
        isStack
      >
        {config ? (
          <Split hasGutter>
            <SplitItem isFilled>
              <Controller
                name="syncStartDate"
                control={control}
                rules={{
                  required: 'This field is required',
                  validate: (value) =>
                    value?.trim() !== '' || 'This field is required',
                }}
                render={({field: {value, onChange}}) => (
                  <>
                    <TextInput
                      type="datetime-local"
                      id="sync_start_date"
                      value={value}
                      onChange={(_event, newValue) => onChange(newValue)}
                      validated={
                        errors.syncStartDate
                          ? ValidatedOptions.error
                          : ValidatedOptions.default
                      }
                    />
                    {errors.syncStartDate && (
                      <HelperText>
                        <HelperTextItem variant="error">
                          {errors.syncStartDate.message}
                        </HelperTextItem>
                      </HelperText>
                    )}
                  </>
                )}
              />
            </SplitItem>
            <SplitItem>
              <Button
                variant="primary"
                size="sm"
                type="button"
                isLoading={isSyncingNow}
                isDisabled={
                  isSyncingNow ||
                  config.sync_status === 'SYNCING' ||
                  config.sync_status === 'SYNC_NOW'
                }
                data-testid="sync-now-button"
                onClick={onSyncNow}
              >
                Sync Now
              </Button>
            </SplitItem>
          </Split>
        ) : (
          <FormTextInput
            name="syncStartDate"
            control={control}
            errors={errors}
            label=""
            fieldId="sync_start_date"
            type="datetime-local"
            required
            isStack={false}
          />
        )}
      </FormGroup>

      <FormGroup label="Sync Interval" fieldId="sync_interval" isStack>
        <InputGroup>
          <Controller
            name="syncValue"
            control={control}
            rules={{
              required: 'This field is required',
              validate: (value) => {
                if (!value || value.trim() === '') {
                  return 'This field is required';
                }
                const numValue = Number(value);
                if (isNaN(numValue) || numValue <= 0) {
                  return 'Must be a positive number';
                }
                return true;
              },
            }}
            render={({field: {value, onChange}}) => (
              <TextInput
                type="text"
                id="sync_interval"
                value={value}
                onChange={(_event, newValue) => {
                  const numericValue = newValue.replace(/[^0-9]/g, '');
                  onChange(numericValue);
                }}
                pattern="[0-9]*"
                inputMode="numeric"
                validated={
                  errors.syncValue
                    ? ValidatedOptions.error
                    : ValidatedOptions.default
                }
                aria-label="Sync interval value"
                data-testid="sync-interval-input"
              />
            )}
          />
          <Controller
            name="syncUnit"
            control={control}
            render={({field: {value, onChange}}) => (
              <Select
                isOpen={isSyncUnitOpen}
                onOpenChange={(isOpen) => setIsSyncUnitOpen(isOpen)}
                onSelect={(_event, selectedValue) => {
                  onChange(selectedValue as string);
                  setIsSyncUnitOpen(false);
                }}
                selected={value}
                aria-label="Sync interval unit"
                toggle={(toggleRef) => (
                  <MenuToggle
                    ref={toggleRef}
                    onClick={() => setIsSyncUnitOpen(!isSyncUnitOpen)}
                    isExpanded={isSyncUnitOpen}
                    data-testid="sync-unit-toggle"
                  >
                    {value}
                  </MenuToggle>
                )}
              >
                <SelectOption value="seconds">seconds</SelectOption>
                <SelectOption value="minutes">minutes</SelectOption>
                <SelectOption value="hours">hours</SelectOption>
                <SelectOption value="days">days</SelectOption>
                <SelectOption value="weeks">weeks</SelectOption>
              </Select>
            )}
          />
        </InputGroup>
        {errors.syncValue && (
          <HelperText>
            <HelperTextItem variant="error">
              {errors.syncValue.message}
            </HelperTextItem>
          </HelperText>
        )}
      </FormGroup>

      <FormGroup label="Skopeo Timeout" fieldId="skopeo_timeout" isStack>
        <Controller
          name="skopeoTimeout"
          control={control}
          rules={{
            required: 'This field is required',
            validate: (value) => {
              if (!value || value < 30) {
                return 'Minimum timeout is 30 seconds';
              }
              if (value > 3600) {
                return 'Maximum timeout is 3600 seconds (1 hour)';
              }
              return true;
            },
          }}
          render={({field: {value, onChange}}) => (
            <InputGroup>
              <TextInput
                type="number"
                id="skopeo_timeout"
                value={value?.toString() || ''}
                onChange={(_event, newValue) => {
                  if (newValue === '') {
                    onChange(null);
                    return;
                  }
                  const parsed = parseInt(newValue, 10);
                  if (!isNaN(parsed)) {
                    onChange(parsed);
                  }
                }}
                min="30"
                max="3600"
                validated={
                  errors.skopeoTimeout
                    ? ValidatedOptions.error
                    : ValidatedOptions.default
                }
                aria-label="Skopeo timeout"
                data-testid="skopeo-timeout-input"
              />
              <InputGroupText>seconds</InputGroupText>
            </InputGroup>
          )}
        />
        {errors.skopeoTimeout ? (
          <HelperText>
            <HelperTextItem variant="error">
              {errors.skopeoTimeout.message}
            </HelperTextItem>
          </HelperText>
        ) : (
          <HelperText>
            <HelperTextItem>
              Timeout for Skopeo operations. Minimum: 30 seconds, Maximum: 3600
              seconds (1 hour).
            </HelperTextItem>
          </HelperText>
        )}
      </FormGroup>
    </>
  );
};
