import React from 'react';
import {Control, FieldErrors, Controller} from 'react-hook-form';
import {
  FormGroup,
  FormHelperText,
  TextInput,
  Button,
  Content,
  Title,
  InputGroup,
  InputGroupText,
  Select,
  SelectOption,
  MenuToggle,
  ValidatedOptions,
} from '@patternfly/react-core';
import {FormTextInput} from 'src/components/forms/FormTextInput';
import {FormCheckbox} from 'src/components/forms/FormCheckbox';
import EntitySearch from 'src/components/EntitySearch';
import {Entity} from 'src/resources/UserResource';
import {AlertVariant} from 'src/atoms/AlertState';
import {
  MirroringConfigResponse,
  getMirrorConfig,
  toggleMirroring,
  syncMirror,
} from 'src/resources/MirroringResource';
import {MirroringFormData} from './types';

interface MirroringConfigurationProps {
  control: Control<MirroringFormData>;
  errors: FieldErrors<MirroringFormData>;
  formValues: MirroringFormData;
  config: MirroringConfigResponse | null;
  namespace: string;
  repoName: string;
  selectedRobot: Entity | null;
  setSelectedRobot: (robot: Entity | null) => void;
  isSelectOpen: boolean;
  setIsSelectOpen: (open: boolean) => void;
  isHovered: boolean;
  setIsHovered: (hovered: boolean) => void;
  robotOptions: React.ReactNode[];
  setConfig: (config: MirroringConfigResponse) => void;
  addAlert: (alert: {
    variant: AlertVariant;
    title: string;
    message?: string;
  }) => void;
}

export const MirroringConfiguration: React.FC<MirroringConfigurationProps> = ({
  control,
  errors,
  formValues,
  config,
  namespace,
  repoName,
  selectedRobot,
  setSelectedRobot,
  isSelectOpen,
  setIsSelectOpen,
  isHovered,
  setIsHovered,
  robotOptions,
  setConfig,
  addAlert,
}) => {
  return (
    <>
      <Title headingLevel="h3">
        {config ? 'Configuration' : 'External Repository'}
      </Title>

      {config && (
        <FormCheckbox
          name="isEnabled"
          control={control}
          label="Enabled"
          fieldId="is_enabled"
          description={
            formValues.isEnabled
              ? 'Scheduled mirroring enabled. Immediate sync available via Sync Now.'
              : 'Scheduled mirroring disabled. Immediate sync available via Sync Now.'
          }
          data-testid="mirror-enabled-checkbox"
          customOnChange={async (checked, onChange) => {
            try {
              await toggleMirroring(namespace, repoName, checked);
              onChange(checked);
              addAlert({
                variant: AlertVariant.Success,
                title: `Mirror ${
                  checked ? 'enabled' : 'disabled'
                } successfully`,
              });
            } catch (err) {
              addAlert({
                variant: AlertVariant.Failure,
                title: 'Error toggling mirror',
                message: err.message,
              });
            }
          }}
        />
      )}

      <FormTextInput
        name="externalReference"
        control={control}
        errors={errors}
        label="Registry Location"
        fieldId="external_reference"
        placeholder="quay.io/redhat/quay"
        required
        data-testid="registry-location-input"
      />

      <FormTextInput
        name="tags"
        control={control}
        errors={errors}
        label="Tags"
        fieldId="tags"
        placeholder="Examples: latest, 3.3*, *"
        required
        helperText="Comma-separated list of tag patterns to synchronize."
        data-testid="tags-input"
      />

      <FormGroup
        label={config ? 'Next Sync Date' : 'Start Date'}
        fieldId="sync_start_date"
        isStack
      >
        {config ? (
          <div style={{display: 'flex', alignItems: 'center', gap: '8px'}}>
            <Controller
              name="syncStartDate"
              control={control}
              rules={{
                required: 'This field is required',
                validate: (value) =>
                  value?.trim() !== '' || 'This field is required',
              }}
              render={({field: {value, onChange}}) => (
                <div style={{flex: 1}}>
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
                    <FormHelperText>
                      <Content
                        component="p"
                        className="pf-m-error pf-v6-u-mt-sm"
                      >
                        {errors.syncStartDate.message}
                      </Content>
                    </FormHelperText>
                  )}
                </div>
              )}
            />
            <Button
              variant="primary"
              size="sm"
              type="button"
              isDisabled={
                config.sync_status === 'SYNCING' ||
                config.sync_status === 'SYNC_NOW'
              }
              data-testid="sync-now-button"
              onClick={async () => {
                try {
                  await syncMirror(namespace, repoName);
                  addAlert({
                    variant: AlertVariant.Success,
                    title: 'Sync scheduled successfully',
                  });
                  const response = await getMirrorConfig(namespace, repoName);
                  setConfig(response);
                } catch (err) {
                  addAlert({
                    variant: AlertVariant.Failure,
                    title: 'Error scheduling sync',
                    message: err.message,
                  });
                }
              }}
            >
              Sync Now
            </Button>
          </div>
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
        <InputGroup
          onPointerEnterCapture={() => setIsHovered(true)}
          onPointerLeaveCapture={() => setIsHovered(false)}
          className={isHovered ? 'pf-v6-u-background-color-200' : ''}
        >
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
                isOpen={isSelectOpen}
                onOpenChange={(isOpen) => setIsSelectOpen(isOpen)}
                onSelect={(_event, selectedValue) => {
                  onChange(selectedValue as string);
                  setIsSelectOpen(false);
                }}
                selected={value}
                aria-label="Sync interval unit"
                toggle={(toggleRef) => (
                  <MenuToggle
                    ref={toggleRef}
                    onClick={() => setIsSelectOpen(!isSelectOpen)}
                    isExpanded={isSelectOpen}
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
          <FormHelperText>
            <Content component="p" className="pf-m-error">
              {errors.syncValue.message}
            </Content>
          </FormHelperText>
        )}
      </FormGroup>

      <FormGroup
        label="Skopeo timeout interval"
        fieldId="skopeo_timeout_interval"
        isStack
      >
        <Controller
          name="skopeoTimeoutInterval"
          control={control}
          rules={{
            required: 'This field is required',
            validate: (value) => {
              if (!value || value < 300) {
                return 'Minimum timeout is 300 seconds (5 minutes)';
              }
              if (value > 43200) {
                return 'Maximum timeout is 43200 seconds (12 hours)';
              }
              return true;
            },
          }}
          render={({field: {value, onChange}}) => (
            <InputGroup
              onPointerEnterCapture={() => setIsHovered(true)}
              onPointerLeaveCapture={() => setIsHovered(false)}
              className={isHovered ? 'pf-v6-u-background-color-200' : ''}
            >
              <TextInput
                type="number"
                id="skopeo_timeout_interval"
                value={value?.toString() || ''}
                onChange={(_event, newValue) => {
                  const numericValue = parseInt(newValue) || 300;
                  onChange(numericValue);
                }}
                min="300"
                max="43200"
                validated={
                  errors.skopeoTimeoutInterval
                    ? ValidatedOptions.error
                    : ValidatedOptions.default
                }
                aria-label="Skopeo timeout interval"
                data-testid="skopeo-timeout-input"
              />
              <InputGroupText>seconds</InputGroupText>
            </InputGroup>
          )}
        />
        {errors.skopeoTimeoutInterval && (
          <FormHelperText>
            <Content component="p" className="pf-m-error">
              {errors.skopeoTimeoutInterval.message}
            </Content>
          </FormHelperText>
        )}
        <FormHelperText>
          <Content component="p">
            Minimum timeout length: 300 seconds (5 minutes). Maximum timeout
            length: 43200 seconds (12 hours).
          </Content>
        </FormHelperText>
      </FormGroup>

      <FormGroup label="Robot User" fieldId="robot_username" isStack>
        <Controller
          name="robotUsername"
          control={control}
          rules={{
            required: 'This field is required',
            validate: (value) =>
              value?.trim() !== '' || 'This field is required',
          }}
          render={({field}) => (
            <>
              <EntitySearch
                id="robot-user-select"
                org={namespace}
                includeTeams={true}
                onSelect={(robot: Entity) => {
                  setSelectedRobot(robot);
                  field.onChange(robot.name);
                }}
                onClear={() => {
                  setSelectedRobot(null);
                  field.onChange('');
                }}
                value={selectedRobot?.name}
                onError={() =>
                  addAlert({
                    variant: AlertVariant.Failure,
                    title: 'Error loading robot users',
                    message: 'Failed to load available robots',
                  })
                }
                defaultOptions={robotOptions}
                placeholderText="Select a team or user..."
                data-testid="robot-user-select"
              />
              {errors.robotUsername && (
                <FormHelperText>
                  <Content component="p" className="pf-m-error">
                    {errors.robotUsername.message}
                  </Content>
                </FormHelperText>
              )}
            </>
          )}
        />
      </FormGroup>
    </>
  );
};
