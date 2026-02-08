import React from 'react';
import {Control, FieldErrors} from 'react-hook-form';
import {Title} from '@patternfly/react-core';
import {FormCheckbox} from 'src/components/forms/FormCheckbox';
import {Entity} from 'src/resources/UserResource';
import {AlertVariant} from 'src/contexts/UIContext';
import {OrgMirrorConfig} from 'src/resources/OrgMirrorResource';
import {OrgMirroringFormData} from './types';
import {OrgMirroringSource} from './OrgMirroringSource';
import {OrgMirroringSyncSchedule} from './OrgMirroringSyncSchedule';
import {OrgMirroringRobotUser} from './OrgMirroringRobotUser';

interface OrgMirroringConfigurationProps {
  control: Control<OrgMirroringFormData>;
  errors: FieldErrors<OrgMirroringFormData>;
  isEnabled: boolean;
  config: OrgMirrorConfig | null;
  orgName: string;
  selectedRobot: Entity | null;
  setSelectedRobot: (robot: Entity | null) => void;
  robotOptions: React.ReactNode[];
  isSyncingNow: boolean;
  onSyncNow: () => Promise<void>;
  onToggleEnabled: (
    checked: boolean,
    onChange: (value: boolean) => void,
  ) => Promise<void>;
  addAlert: (alert: {
    variant: AlertVariant;
    title: string;
    message?: string;
  }) => void;
}

export const OrgMirroringConfiguration: React.FC<
  OrgMirroringConfigurationProps
> = ({
  control,
  errors,
  isEnabled,
  config,
  orgName,
  selectedRobot,
  setSelectedRobot,
  robotOptions,
  isSyncingNow,
  onSyncNow,
  onToggleEnabled,
  addAlert,
}) => {
  return (
    <>
      <Title headingLevel="h3">
        {config ? 'Configuration' : 'Source Registry'}
      </Title>

      {config && (
        <FormCheckbox
          name="isEnabled"
          control={control}
          label="Enabled"
          fieldId="is_enabled"
          description={
            isEnabled
              ? 'Scheduled organization mirroring enabled.'
              : 'Scheduled organization mirroring disabled.'
          }
          data-testid="org-mirror-enabled-checkbox"
          customOnChange={(checked, onChange) => {
            void onToggleEnabled(checked, onChange);
          }}
        />
      )}

      <OrgMirroringSource control={control} errors={errors} />

      <OrgMirroringSyncSchedule
        control={control}
        errors={errors}
        config={config}
        isSyncingNow={isSyncingNow}
        onSyncNow={onSyncNow}
      />

      <OrgMirroringRobotUser
        control={control}
        errors={errors}
        orgName={orgName}
        selectedRobot={selectedRobot}
        setSelectedRobot={setSelectedRobot}
        robotOptions={robotOptions}
        addAlert={addAlert}
      />
    </>
  );
};
