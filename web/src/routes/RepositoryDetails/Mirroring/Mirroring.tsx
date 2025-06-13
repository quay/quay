import React, {useState} from 'react';
import {
  Form,
  FormGroup,
  TextInput,
  Checkbox,
  Button,
  ButtonVariant,
  ActionGroup,
  Divider,
  Text,
  TextContent,
  Title,
  InputGroup,
  Select,
  SelectOption,
  MenuToggle,
} from '@patternfly/react-core';
import {useRepository} from 'src/hooks/UseRepository';
import './Mirroring.css';

interface MirroringProps {
  organization: string;
  repository: string;
}

export const Mirroring: React.FC<MirroringProps> = ({
  organization,
  repository,
}) => {
  const {repoDetails} = useRepository(organization, repository);
  const [syncValue, setSyncValue] = useState('');
  const [isSelectOpen, setIsSelectOpen] = useState(false);
  const [syncUnit, setSyncUnit] = useState('minutes');
  const [isHovered, setIsHovered] = useState(false);

  if (!repoDetails) {
    return <Text>Repository not found</Text>;
  }

  return (
    <div className="mirroring-container">
      <TextContent>
        <Title headingLevel="h2">Repository Mirroring</Title>
      </TextContent>
      <TextContent>
        This feature will convert the repository into a mirror. Changes to the
        external repository will be duplicated here. While enabled, users will
        be unable to push images to this repository.
      </TextContent>
      <Form isWidthLimited>
        <Divider />

        <Title headingLevel="h3" className="mirroring-section-title">
          External Repository
        </Title>
        <FormGroup
          label="Registry Location"
          fieldId="external_reference"
          isStack
        >
          <TextInput
            type="text"
            id="external_reference"
            name="external_reference"
            placeholder="quay.io/redhat/quay"
          />
        </FormGroup>

        <FormGroup label="Tags" fieldId="tags" isStack>
          <TextInput
            type="text"
            id="tags"
            name="tags"
            placeholder="Examples: latest, 3.3*, *"
          />
        </FormGroup>

        <FormGroup label="Start Date" fieldId="sync_start_date" isStack>
          <TextInput
            type="datetime-local"
            id="sync_start_date"
            name="sync_start_date"
          />
        </FormGroup>

        <FormGroup label="Sync Interval" fieldId="sync_interval" isStack>
          <InputGroup
            onPointerEnterCapture={() => setIsHovered(true)}
            onPointerLeaveCapture={() => setIsHovered(false)}
            className={isHovered ? 'pf-v5-u-background-color-200' : ''}
          >
            <TextInput
              type="number"
              id="sync_interval"
              name="sync_interval"
              value={syncValue}
              onChange={(_event, value) => setSyncValue(value)}
              aria-label="Sync interval value"
            />
            <Select
              isOpen={isSelectOpen}
              onOpenChange={(isOpen) => setIsSelectOpen(isOpen)}
              onSelect={(_event, value) => {
                setSyncUnit(value as string);
                setIsSelectOpen(false);
              }}
              selected={syncUnit}
              aria-label="Sync interval unit"
              toggle={(toggleRef) => (
                <MenuToggle
                  ref={toggleRef}
                  onClick={() => setIsSelectOpen(!isSelectOpen)}
                  isExpanded={isSelectOpen}
                >
                  {syncUnit}
                </MenuToggle>
              )}
            >
              <SelectOption value="seconds">seconds</SelectOption>
              <SelectOption value="minutes">minutes</SelectOption>
              <SelectOption value="hours">hours</SelectOption>
              <SelectOption value="days">days</SelectOption>
              <SelectOption value="weeks">weeks</SelectOption>
            </Select>
          </InputGroup>
        </FormGroup>

        <FormGroup label="Robot User" fieldId="robot_username" isStack>
          <TextInput type="text" id="robot_username" name="robot_username" />
        </FormGroup>

        <Divider />
        <Title headingLevel="h3" className="mirroring-section-title">
          Credentials
        </Title>
        <Text
          component="small"
          className="pf-v5-c-form__helper-text mirroring-credentials-helper"
        >
          Required if the external repository is private.
        </Text>
        <FormGroup label="Username" fieldId="username" isStack>
          <TextInput type="text" id="username" name="username" />
        </FormGroup>

        <FormGroup
          label="Password"
          fieldId="external_registry_password"
          isStack
        >
          <TextInput
            type="password"
            id="external_registry_password"
            name="external_registry_password"
          />
        </FormGroup>

        <Divider />
        <Title headingLevel="h3" className="mirroring-section-title">
          Advanced Settings
        </Title>
        <FormGroup fieldId="verify_tls" isStack>
          <Checkbox
            label="Verify TLS"
            id="verify_tls"
            name="verify_tls"
            description="Require HTTPS and verify certificates when talking to the external registry."
          />
        </FormGroup>

        <FormGroup fieldId="unsigned_images" isStack>
          <Checkbox
            label="Accept Unsigned Images"
            id="unsigned_images"
            name="unsigned_images"
            description="Allow unsigned images to be mirrored."
          />
        </FormGroup>

        <FormGroup label="HTTP Proxy" fieldId="http_proxy" isStack>
          <TextInput
            type="text"
            id="http_proxy"
            name="http_proxy"
            placeholder="proxy.example.com"
          />
        </FormGroup>

        <FormGroup label="HTTPs Proxy" fieldId="https_proxy" isStack>
          <TextInput
            type="text"
            id="https_proxy"
            name="https_proxy"
            placeholder="proxy.example.com"
          />
        </FormGroup>

        <FormGroup label="No Proxy" fieldId="no_proxy" isStack>
          <TextInput
            type="text"
            id="no_proxy"
            name="no_proxy"
            placeholder="example.com"
          />
        </FormGroup>

        <ActionGroup>
          <Button variant={ButtonVariant.primary} className="mirroring-button">
            Enable Mirror
          </Button>
        </ActionGroup>
      </Form>
    </div>
  );
};
