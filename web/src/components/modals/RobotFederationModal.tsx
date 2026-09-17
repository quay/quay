import {IRobot, IRobotFederationConfig} from 'src/resources/RobotsResource';
import {
  ActionGroup,
  Button,
  Checkbox,
  Flex,
  FlexItem,
  Form,
  FormFieldGroupExpandable,
  FormFieldGroupHeader,
  FormGroup,
  Spinner,
  Stack,
  StackItem,
  TextInput,
} from '@patternfly/react-core';
import {PlusIcon, TrashIcon} from '@patternfly/react-icons';
import React, {useEffect, useState} from 'react';
import DisplayModal from './robotAccountWizard/DisplayModal';
import {useRobotFederation} from 'src/hooks/useRobotFederation';
import {AlertVariant, useUI} from 'src/contexts/UIContext';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {OAUTH_SCOPES} from 'src/routes/OrganizationsList/Organization/Tabs/OAuthApplications/types';

type FederationFormEntry = IRobotFederationConfig & {isExpanded?: boolean};

function RobotFederationForm(props: RobotFederationFormProps) {
  const [federationFormState, setFederationFormState] = useState<
    FederationFormEntry[]
  >([]);
  const {addAlert} = useUI();
  const quayConfig = useQuayConfig();

  const {robotFederationConfig, loading, fetchError, setRobotFederationConfig} =
    useRobotFederation({
      namespace: props.namespace,
      robotName: props.robotAccount.name,
      onSuccess: (result) => {
        setFederationFormState(
          result.map((config) => ({...config, isExpanded: false})),
        );
        addAlert({
          title: 'Robot federation config saved',
          variant: AlertVariant.Success,
        });
      },
      onError: (e) => {
        addAlert({
          title: e.error_message || 'Error saving federation config',
          variant: AlertVariant.Failure,
        });
      },
    });

  useEffect(() => {
    if (robotFederationConfig) {
      setFederationFormState(
        robotFederationConfig.map((config) => ({...config, isExpanded: false})),
      );
    }
  }, [robotFederationConfig]);

  if (loading) {
    return <Spinner size="md" />;
  }

  if (fetchError) {
    return <div>Error fetching federation config</div>;
  }

  const addFederationConfigEntry = () => {
    setFederationFormState((prev) => [
      ...prev,
      {issuer: '', subject: '', api_scopes: '', isExpanded: true},
    ]);
  };

  const updateFederationConfigEntry = (
    index: number,
    updates: Partial<FederationFormEntry>,
  ) => {
    setFederationFormState((prev) =>
      prev.map((config, i) => (i === index ? {...config, ...updates} : config)),
    );
  };

  const removeFederationConfigEntry = (index: number) => {
    setFederationFormState((prev) => prev.filter((_, i) => i !== index));
  };

  return (
    <Form>
      {federationFormState.map((config, index) => (
        <RobotFederationFormEntry
          key={config.id || index}
          config={config}
          index={index}
          showSuperuserScope={quayConfig?.features?.SUPER_USERS === true}
          onRemove={removeFederationConfigEntry}
          onUpdate={updateFederationConfigEntry}
        />
      ))}

      <FormGroup>
        <Flex>
          {federationFormState.length === 0 && (
            <FlexItem>
              <div>No federation configured, add using the plus button</div>
            </FlexItem>
          )}
          <FlexItem align={{default: 'alignRight'}}>
            <Button
              icon={<PlusIcon />}
              aria-label="Add federation entry"
              onClick={addFederationConfigEntry}
            />
          </FlexItem>
        </Flex>
      </FormGroup>
      <ActionGroup>
        <Button
          variant="primary"
          onClick={() =>
            setRobotFederationConfig({
              namespace: props.namespace,
              robotName: props.robotAccount.name,
              config: federationFormState,
            })
          }
        >
          Save
        </Button>
        <Button variant="link" onClick={props.onClose}>
          Close
        </Button>
      </ActionGroup>
    </Form>
  );
}

interface RobotFederationFormEntryProps {
  config: FederationFormEntry;
  index: number;
  showSuperuserScope: boolean;
  onRemove: (index: number) => void;
  onUpdate: (index: number, updates: Partial<FederationFormEntry>) => void;
}

function RobotFederationFormEntry({
  config,
  index,
  showSuperuserScope,
  onRemove,
  onUpdate,
}: RobotFederationFormEntryProps) {
  const selectedScopes = config.api_scopes?.split(' ').filter(Boolean) || [];
  const toggleScope = (scope: string, checked: boolean) => {
    const nextScopes = checked
      ? [...selectedScopes, scope]
      : selectedScopes.filter((selected) => selected !== scope);
    onUpdate(index, {api_scopes: nextScopes.join(' ')});
  };

  return (
    <FormFieldGroupExpandable
      isExpanded={config.isExpanded}
      header={
        <FormFieldGroupHeader
          titleText={{
            text: `${config.issuer} : ${config.subject}`,
            id: `${index}-issuer-url`,
          }}
          actions={
            <Button
              icon={<TrashIcon />}
              aria-label="Remove federation entry"
              onClick={() => onRemove(index)}
              variant="danger"
            />
          }
        />
      }
    >
      <FormGroup label="Issuer URL" isRequired>
        <TextInput
          value={config.issuer}
          type="text"
          isRequired
          onChange={(_event, value) => onUpdate(index, {issuer: value})}
        />
      </FormGroup>
      <FormGroup label="Subject" isRequired>
        <TextInput
          value={config.subject}
          type="text"
          isRequired
          onChange={(_event, value) => onUpdate(index, {subject: value})}
        />
      </FormGroup>
      <FormGroup
        label="Management API and registry scopes"
        helperText="Optional. A configured scope makes federation JWTs valid for both Management API Bearer authentication and scoped registry push/pull. Leave empty for registry-only federation."
      >
        <Stack hasGutter>
          {Object.entries(OAUTH_SCOPES)
            .filter(
              ([scope]) =>
                scope !== 'direct_user_login' &&
                (scope !== 'super:user' || showSuperuserScope),
            )
            .map(([scope, details]) => (
              <StackItem key={scope}>
                <Checkbox
                  id={`robot-federation-${index}-scope-${scope}`}
                  label={details.title}
                  description={details.description}
                  isChecked={selectedScopes.includes(scope)}
                  onChange={(_event, checked) => toggleScope(scope, checked)}
                />
              </StackItem>
            ))}
        </Stack>
      </FormGroup>
    </FormFieldGroupExpandable>
  );
}

export function RobotFederationModal(props: RobotFederationModalProps) {
  return (
    <DisplayModal
      isModalOpen={props.isModalOpen}
      setIsModalOpen={props.setIsModalOpen}
      title={`Robot identity federation configuration for ${props.robotAccount.name}`}
      Component={
        <RobotFederationForm
          robotAccount={props.robotAccount}
          namespace={props.namespace}
          onClose={() => props.setIsModalOpen(false)}
        />
      }
      showSave={false}
      showFooter={false}
    />
  );
}

interface RobotFederationModalProps {
  robotAccount: IRobot;
  namespace: string;
  isModalOpen: boolean;
  setIsModalOpen: (modalState: boolean) => void;
}

interface RobotFederationFormProps {
  robotAccount: IRobot;
  namespace: string;
  onClose: () => void;
}
