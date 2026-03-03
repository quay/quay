import React, {useState} from 'react';
import {Control, FieldErrors, Controller} from 'react-hook-form';
import {
  FormGroup,
  HelperText,
  HelperTextItem,
  TextInput,
  Button,
  InputGroup,
  InputGroupItem,
  InputGroupText,
  Select,
  SelectOption,
  MenuToggle,
  ValidatedOptions,
  Split,
  SplitItem,
  DatePicker,
  TimePicker,
} from '@patternfly/react-core';
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

  const parseSyncDate = (value: string): Date | null => {
    if (!value) return null;
    const d = new Date(value);
    return isNaN(d.getTime()) ? null : d;
  };

  const dateFormat = (date: Date): string =>
    date.toLocaleDateString(navigator.language, {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });

  const formatTime = (date: Date | null): string => {
    if (!date) return '';
    const h = String(date.getHours()).padStart(2, '0');
    const m = String(date.getMinutes()).padStart(2, '0');
    return `${h}:${m}`;
  };

  const toFormString = (date: Date): string => {
    const y = date.getFullYear();
    const mo = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    const h = String(date.getHours()).padStart(2, '0');
    const mi = String(date.getMinutes()).padStart(2, '0');
    return `${y}-${mo}-${d}T${h}:${mi}`;
  };

  const renderDateTimePicker = (
    value: string,
    onChange: (val: string) => void,
  ) => {
    const current = parseSyncDate(value);

    const onDateChange = (
      _event: React.FormEvent<HTMLInputElement>,
      _value: string,
      dateValue?: Date,
    ) => {
      if (dateValue === null || dateValue === undefined) return;
      const newDate = current ? new Date(current) : new Date();
      // Set day to 1 first to avoid JS date rollover when changing months
      newDate.setDate(1);
      newDate.setFullYear(dateValue.getFullYear());
      newDate.setMonth(dateValue.getMonth());
      newDate.setDate(dateValue.getDate());
      if (!current) {
        newDate.setHours(0, 0, 0, 0);
      }
      onChange(toFormString(newDate));
    };

    const onTimeChange = (
      _event: React.FormEvent<HTMLInputElement>,
      _time: string,
      hour?: number,
      minute?: number,
      _seconds?: number,
      isValid?: boolean,
    ) => {
      if (hour == null || minute == null || !isValid) return;
      const newDate = current ? new Date(current) : new Date();
      newDate.setHours(hour, minute);
      onChange(toFormString(newDate));
    };

    return (
      <InputGroup>
        <InputGroupItem>
          <DatePicker
            value={current ? dateFormat(current) : ''}
            dateFormat={dateFormat}
            dateParse={(str: string) => new Date(str)}
            onChange={onDateChange}
            aria-label="Sync start date"
          />
        </InputGroupItem>
        <InputGroupItem>
          <TimePicker
            time={formatTime(current)}
            onChange={onTimeChange}
            is24Hour
            aria-label="Sync start time"
            style={{width: '150px'}}
          />
        </InputGroupItem>
      </InputGroup>
    );
  };

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
                    {renderDateTimePicker(value, onChange)}
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
                {renderDateTimePicker(value, onChange)}
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
