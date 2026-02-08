import React from 'react';
import {Control, FieldErrors, Controller} from 'react-hook-form';
import {FormGroup, HelperText, HelperTextItem} from '@patternfly/react-core';
import EntitySearch from 'src/components/EntitySearch';
import {Entity} from 'src/resources/UserResource';
import {AlertVariant} from 'src/contexts/UIContext';
import {OrgMirroringFormData} from './types';

interface OrgMirroringRobotUserProps {
  control: Control<OrgMirroringFormData>;
  errors: FieldErrors<OrgMirroringFormData>;
  orgName: string;
  selectedRobot: Entity | null;
  setSelectedRobot: (robot: Entity | null) => void;
  robotOptions: React.ReactNode[];
  addAlert: (alert: {
    variant: AlertVariant;
    title: string;
    message?: string;
  }) => void;
}

export const OrgMirroringRobotUser: React.FC<OrgMirroringRobotUserProps> = ({
  control,
  errors,
  orgName,
  selectedRobot,
  setSelectedRobot,
  robotOptions,
  addAlert,
}) => {
  return (
    <FormGroup label="Robot User" fieldId="robot_username" isStack>
      <Controller
        name="robotUsername"
        control={control}
        rules={{
          required: 'This field is required',
          validate: (value) => value?.trim() !== '' || 'This field is required',
        }}
        render={({field}) => (
          <>
            <EntitySearch
              id="robot-user-select"
              org={orgName}
              includeTeams={false}
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
              placeholderText="Select a robot user..."
              data-testid="robot-user-select"
            />
            {errors.robotUsername && (
              <HelperText>
                <HelperTextItem variant="error">
                  {errors.robotUsername.message}
                </HelperTextItem>
              </HelperText>
            )}
          </>
        )}
      />
    </FormGroup>
  );
};
