import {
  fetchRobotMintableScopes,
  IRobot,
  IRobotFederationConfig,
} from 'src/resources/RobotsResource';
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
import {useQuery} from '@tanstack/react-query';
import React, {useEffect, useRef, useState} from 'react';
import DisplayModal from './robotAccountWizard/DisplayModal';
import {useRobotFederation} from 'src/hooks/useRobotFederation';
import {AlertVariant, useUI} from 'src/contexts/UIContext';
import {OAUTH_SCOPES} from 'src/routes/OrganizationsList/Organization/Tabs/OAuthApplications/types';

type FederationFormEntry = IRobotFederationConfig & {
  isExpanded?: boolean;
  uiKey?: number;
};

function RobotFederationForm(props: RobotFederationFormProps) {
  const [federationFormState, setFederationFormState] = useState<
    FederationFormEntry[]
  >([]);
  const {addAlert} = useUI();
  const nextFormEntryKey = useRef(0);

  const {robotFederationConfig, loading, fetchError, setRobotFederationConfig} =
    useRobotFederation({
      namespace: props.namespace,
      robotName: props.robotAccount.name,
      onSuccess: (result) => {
        setFederationFormState(
          result.map((config) => ({
            ...config,
            isExpanded: false,
            uiKey: config.id ? undefined : nextFormEntryKey.current++,
          })),
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
        robotFederationConfig.map((config) => ({
          ...config,
          isExpanded: false,
          uiKey: config.id ? undefined : nextFormEntryKey.current++,
        })),
      );
    }
  }, [robotFederationConfig]);

  const {
    data: mintableScopes = [],
    isLoading: isLoadingMintableScopes,
    isError: isMintableScopesError,
  } = useQuery(
    [
      'robot-mintable-scopes',
      props.namespace,
      props.robotAccount.name,
      props.isUser,
    ],
    () =>
      fetchRobotMintableScopes(
        props.namespace,
        props.robotAccount.name,
        props.isUser,
      ),
  );
  const hasInaccessibleScopes = federationFormState.some((config) =>
    config.api_scopes
      ?.split(/[ ,]+/)
      .filter(Boolean)
      .some((scope) => !mintableScopes.includes(scope)),
  );
  const canSave =
    !isLoadingMintableScopes &&
    !isMintableScopesError &&
    !hasInaccessibleScopes;

  if (loading) {
    return <Spinner size="md" />;
  }

  if (fetchError) {
    return <div>Error fetching federation config</div>;
  }

  const addFederationConfigEntry = () => {
    setFederationFormState((prev) => [
      ...prev,
      {
        issuer: '',
        subject: '',
        audiences: ['quay'],
        api_scopes: '',
        isExpanded: true,
        uiKey: nextFormEntryKey.current++,
      },
    ]);
  };

  const saveFederationConfig = () => {
    setRobotFederationConfig({
      namespace: props.namespace,
      robotName: props.robotAccount.name,
      config: federationFormState.map(
        ({isExpanded, uiKey, ...config}) => config,
      ),
    });
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
    <Form
      onSubmit={(event) => {
        event.preventDefault();
        if (canSave) {
          saveFederationConfig();
        }
      }}
    >
      {federationFormState.map((config, index) => (
        <RobotFederationFormEntry
          key={config.id || config.uiKey}
          config={config}
          index={index}
          mintableScopes={mintableScopes}
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
              type="button"
              onClick={addFederationConfigEntry}
            />
          </FlexItem>
        </Flex>
      </FormGroup>
      {isLoadingMintableScopes && <Spinner size="md" />}
      {isMintableScopesError && <div>Unable to load scopes you can grant.</div>}
      {hasInaccessibleScopes && (
        <div>
          One or more configured scopes are no longer available to your account.
          An authorized editor must update this federation configuration.
        </div>
      )}
      <ActionGroup>
        <Button variant="primary" type="submit" isDisabled={!canSave}>
          Save
        </Button>
        <Button variant="link" type="button" onClick={props.onClose}>
          Close
        </Button>
      </ActionGroup>
    </Form>
  );
}

interface RobotFederationFormEntryProps {
  config: FederationFormEntry;
  index: number;
  mintableScopes: string[];
  onRemove: (index: number) => void;
  onUpdate: (index: number, updates: Partial<FederationFormEntry>) => void;
}

function RobotFederationFormEntry({
  config,
  index,
  mintableScopes,
  onRemove,
  onUpdate,
}: RobotFederationFormEntryProps) {
  const normalizedAudiences = (config.audiences || ['quay']).join(', ');
  const [audienceText, setAudienceText] = useState(normalizedAudiences);
  const previousAudiences = useRef(normalizedAudiences);
  const selectedScopes =
    config.api_scopes?.split(/[ ,]+/).filter(Boolean) || [];

  useEffect(() => {
    if (normalizedAudiences !== previousAudiences.current) {
      setAudienceText(normalizedAudiences);
      previousAudiences.current = normalizedAudiences;
    }
  }, [normalizedAudiences]);
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
              type="button"
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
        label="OIDC audiences"
        helperText="Comma-separated token audiences. Defaults to quay."
        isRequired
      >
        <TextInput
          value={audienceText}
          type="text"
          isRequired
          onChange={(_event, value) => {
            setAudienceText(value);
            onUpdate(index, {
              audiences: value
                .split(',')
                .map((audience) => audience.trim())
                .filter(Boolean),
            });
          }}
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
                scope !== 'direct_user_login' && mintableScopes.includes(scope),
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
          isUser={props.isUser}
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
  isUser: boolean;
  isModalOpen: boolean;
  setIsModalOpen: (modalState: boolean) => void;
}

interface RobotFederationFormProps {
  robotAccount: IRobot;
  namespace: string;
  isUser: boolean;
  onClose: () => void;
}
