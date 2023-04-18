import {
  TextContent,
  Text,
  TextVariants,
  TextInput,
  FormGroup,
  Form,
} from '@patternfly/react-core';
import React from 'react';
import {DropdownWithDescription} from 'src/components/toolbar/DropdownWithDescription';

export default function DefaultPermissions(props: DefaultPermissionsProps) {
  const updateDefaultPermission = (permission, repo) => {
    props.setRobotdefaultPerm(permission);
  };

  return (
    <>
      <TextContent>
        <Text component={TextVariants.h1}>Default permissions (Optional)</Text>
        <Text component={TextVariants.p}>
          The Default permissions panel defines permissions that should be
          granted automatically to a repository when it is created, in addition
          to the default of the repository&apos;s creator.
          <br />
          Permissions are assigned based on the user who created the repository.
        </Text>
        <Text component={TextVariants.p}>
          Note: Permissions added here do not automatically get added to
          existing repositories.
        </Text>

        <Form>
          <FormGroup
            label="Applied To"
            fieldId="robot-name"
            isRequired
            disabled
            className="fit-content"
          >
            <TextInput
              value={props.robotName}
              type="text"
              aria-label="robot-name-value"
              isDisabled
            />
          </FormGroup>
          <FormGroup label="Permission" fieldId="robot-permission" isRequired />
        </Form>
      </TextContent>
      <DropdownWithDescription
        dropdownItems={props.repoPermissions}
        onSelect={updateDefaultPermission}
        selectedVal={props.robotDefaultPerm || 'None'}
        wizarStep={true}
      />
    </>
  );
}

interface DefaultPermissionsProps {
  robotName: string;
  repoPermissions: any[];
  robotDefaultPerm: string;
  setRobotdefaultPerm: (perm) => void;
}
