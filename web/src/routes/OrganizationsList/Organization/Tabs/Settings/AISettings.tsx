import {
  ActionGroup,
  Alert,
  Button,
  Form,
  FormGroup,
  FormHelperText,
  FormSelect,
  FormSelectOption,
  HelperText,
  HelperTextItem,
  Spinner,
  Switch,
  TextInput,
} from '@patternfly/react-core';
import {CheckCircleIcon, ExclamationCircleIcon} from '@patternfly/react-icons';
import {useState, useEffect} from 'react';
import {AlertVariant, useUI} from 'src/contexts/UIContext';
import {
  useAISettings,
  useUpdateAISettings,
  useSetAICredentials,
  useDeleteAICredentials,
  useVerifyAICredentials,
} from 'src/hooks/UseAIDescription';
import {VALID_PROVIDERS, AIProvider} from 'src/resources/AIResource';

type AISettingsProps = {
  organizationName: string;
};

const PROVIDER_LABELS: Record<AIProvider, string> = {
  anthropic: 'Anthropic (Claude)',
  openai: 'OpenAI (GPT)',
  google: 'Google (Gemini)',
  deepseek: 'DeepSeek',
  custom: 'Custom (OpenAI-compatible)',
};

const DEFAULT_MODELS: Partial<Record<AIProvider, string>> = {
  anthropic: 'claude-sonnet-4-20250514',
  openai: 'gpt-4o-mini',
  google: 'gemini-2.0-flash-lite',
  deepseek: 'deepseek-chat',
};

export function AISettings({organizationName}: AISettingsProps) {
  const {addAlert} = useUI();

  // Fetch current settings
  const {data: settings, isLoading, error} = useAISettings(organizationName);

  // Form state
  const [provider, setProvider] = useState<AIProvider>('anthropic');
  const [apiKey, setApiKey] = useState('');
  const [model, setModel] = useState('');
  const [endpoint, setEndpoint] = useState('');
  const [descriptionEnabled, setDescriptionEnabled] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);

  // Update form when settings load
  useEffect(() => {
    if (settings) {
      setProvider((settings.provider as AIProvider) || 'anthropic');
      setModel(settings.model || '');
      setEndpoint(settings.endpoint || '');
      setDescriptionEnabled(settings.description_generator_enabled);
      // API key is never returned from server for security
      setApiKey('');
    }
  }, [settings]);

  // Mutations
  const updateSettingsMutation = useUpdateAISettings({
    onSuccess: () => {
      addAlert({
        variant: AlertVariant.Success,
        title: 'AI settings updated successfully',
      });
      setHasChanges(false);
    },
    onError: (err) => {
      addAlert({
        variant: AlertVariant.Failure,
        title: err.message || 'Failed to update AI settings',
      });
    },
  });

  const setCredentialsMutation = useSetAICredentials({
    onSuccess: () => {
      addAlert({
        variant: AlertVariant.Success,
        title: 'AI credentials saved successfully',
      });
      setApiKey('');
      setHasChanges(false);
    },
    onError: (err) => {
      addAlert({
        variant: AlertVariant.Failure,
        title: err.message || 'Failed to save AI credentials',
      });
    },
  });

  const deleteCredentialsMutation = useDeleteAICredentials({
    onSuccess: () => {
      addAlert({
        variant: AlertVariant.Success,
        title: 'AI credentials deleted',
      });
      setApiKey('');
      setModel('');
      setEndpoint('');
      setDescriptionEnabled(false);
    },
    onError: (err) => {
      addAlert({
        variant: AlertVariant.Failure,
        title: err.message || 'Failed to delete AI credentials',
      });
    },
  });

  const verifyCredentialsMutation = useVerifyAICredentials({
    onSuccess: (data) => {
      if (data.valid) {
        addAlert({
          variant: AlertVariant.Success,
          title: 'Credentials verified successfully',
        });
      } else {
        addAlert({
          variant: AlertVariant.Failure,
          title: data.error || 'Credentials verification failed',
        });
      }
    },
    onError: (err) => {
      addAlert({
        variant: AlertVariant.Failure,
        title: err.message || 'Failed to verify credentials',
      });
    },
  });

  const handleProviderChange = (value: string) => {
    const newProvider = value as AIProvider;
    setProvider(newProvider);
    setModel(DEFAULT_MODELS[newProvider] || '');
    setHasChanges(true);
  };

  const handleSaveCredentials = () => {
    if (!apiKey) {
      addAlert({
        variant: AlertVariant.Failure,
        title: 'API key is required',
      });
      return;
    }

    if (provider === 'custom' && !endpoint) {
      addAlert({
        variant: AlertVariant.Failure,
        title: 'Endpoint URL is required for custom providers',
      });
      return;
    }

    setCredentialsMutation.mutate({
      orgName: organizationName,
      credentials: {
        provider,
        api_key: apiKey,
        model: model || undefined,
        endpoint: provider === 'custom' ? endpoint : undefined,
      },
    });
  };

  const handleVerifyCredentials = () => {
    const keyToVerify = apiKey || 'existing';

    verifyCredentialsMutation.mutate({
      orgName: organizationName,
      request: {
        provider,
        api_key: keyToVerify,
        model: model || DEFAULT_MODELS[provider] || '',
        endpoint: provider === 'custom' ? endpoint : undefined,
      },
    });
  };

  const handleDeleteCredentials = () => {
    deleteCredentialsMutation.mutate(organizationName);
  };

  const handleToggleDescription = (checked: boolean) => {
    if (checked && !settings?.credentials_verified) {
      addAlert({
        variant: AlertVariant.Failure,
        title: 'Please configure and verify credentials first',
      });
      return;
    }

    // Store previous state for rollback on error
    const previousEnabled = descriptionEnabled;

    // Optimistic update
    setDescriptionEnabled(checked);

    updateSettingsMutation.mutate(
      {
        orgName: organizationName,
        settings: {
          description_generator_enabled: checked,
        },
      },
      {
        onError: () => {
          // Rollback on error
          setDescriptionEnabled(previousEnabled);
        },
      },
    );
  };

  if (isLoading) {
    return (
      <div style={{textAlign: 'center', padding: '2rem'}}>
        <Spinner size="lg" />
      </div>
    );
  }

  if (error) {
    return (
      <Alert variant="danger" isInline title="Error loading AI settings">
        Unable to load AI settings. This feature may not be enabled for your
        deployment.
      </Alert>
    );
  }

  const isSaving =
    setCredentialsMutation.isLoading || updateSettingsMutation.isLoading;
  const showCustomEndpoint = provider === 'custom';

  return (
    <Form maxWidth="70%">
      <FormGroup label="AI Provider" fieldId="ai-provider" isRequired>
        <FormSelect
          id="ai-provider"
          value={provider}
          onChange={(_event, value) => handleProviderChange(value)}
          aria-label="AI Provider"
        >
          {VALID_PROVIDERS.map((p) => (
            <FormSelectOption key={p} value={p} label={PROVIDER_LABELS[p]} />
          ))}
        </FormSelect>
        <FormHelperText>
          <HelperText>
            <HelperTextItem>
              Select the AI provider for generating repository descriptions.
            </HelperTextItem>
          </HelperText>
        </FormHelperText>
      </FormGroup>

      <FormGroup label="Model" fieldId="ai-model" isRequired>
        <TextInput
          id="ai-model"
          value={model}
          onChange={(_event, value) => {
            setModel(value);
            setHasChanges(true);
          }}
          placeholder={DEFAULT_MODELS[provider] || 'Enter model name'}
        />
        <FormHelperText>
          <HelperText>
            <HelperTextItem>
              The model to use for AI-powered features. Different models have
              different capabilities and costs.
            </HelperTextItem>
          </HelperText>
        </FormHelperText>
      </FormGroup>

      <FormGroup label="API Key" fieldId="ai-api-key" isRequired>
        <TextInput
          id="ai-api-key"
          type="password"
          value={apiKey}
          onChange={(_event, value) => {
            setApiKey(value);
            setHasChanges(true);
          }}
          placeholder={
            settings?.credentials_configured
              ? '••••••••••••••••'
              : 'Enter your API key'
          }
        />
        <FormHelperText>
          <HelperText>
            <HelperTextItem>
              Your API key for the selected provider. This will be stored
              encrypted.
              {settings?.credentials_configured && (
                <> Leave blank to keep existing key.</>
              )}
            </HelperTextItem>
          </HelperText>
        </FormHelperText>
      </FormGroup>

      {showCustomEndpoint && (
        <FormGroup
          label="Custom Endpoint"
          fieldId="ai-endpoint"
          isRequired={showCustomEndpoint}
        >
          <TextInput
            id="ai-endpoint"
            value={endpoint}
            onChange={(_event, value) => {
              setEndpoint(value);
              setHasChanges(true);
            }}
            placeholder="https://your-api.example.com/v1"
          />
          <FormHelperText>
            <HelperText>
              <HelperTextItem>
                The base URL for your OpenAI-compatible API endpoint.
              </HelperTextItem>
            </HelperText>
          </FormHelperText>
        </FormGroup>
      )}

      {/* Credential status */}
      <FormGroup label="Credential Status" fieldId="ai-status">
        {settings?.credentials_verified ? (
          <div style={{display: 'flex', alignItems: 'center', gap: '0.5rem'}}>
            <CheckCircleIcon color="green" />
            <span>Credentials verified</span>
          </div>
        ) : settings?.credentials_configured ? (
          <div style={{display: 'flex', alignItems: 'center', gap: '0.5rem'}}>
            <ExclamationCircleIcon color="orange" />
            <span>Credentials configured but not verified</span>
          </div>
        ) : (
          <div style={{display: 'flex', alignItems: 'center', gap: '0.5rem'}}>
            <ExclamationCircleIcon color="gray" />
            <span>No credentials configured</span>
          </div>
        )}
      </FormGroup>

      <ActionGroup>
        <Button
          variant="primary"
          onClick={handleSaveCredentials}
          isLoading={setCredentialsMutation.isLoading}
          isDisabled={isSaving || (!apiKey && !hasChanges)}
        >
          Save Credentials
        </Button>
        <Button
          variant="secondary"
          onClick={handleVerifyCredentials}
          isLoading={verifyCredentialsMutation.isLoading}
          isDisabled={
            isSaving ||
            verifyCredentialsMutation.isLoading ||
            (!settings?.credentials_configured && !apiKey)
          }
        >
          Verify Credentials
        </Button>
        {settings?.credentials_configured && (
          <Button
            variant="danger"
            onClick={handleDeleteCredentials}
            isLoading={deleteCredentialsMutation.isLoading}
            isDisabled={isSaving}
          >
            Delete Credentials
          </Button>
        )}
      </ActionGroup>

      <hr style={{margin: '2rem 0', borderColor: '#d2d2d2'}} />

      <FormGroup
        label="AI Description Generator"
        fieldId="ai-description-toggle"
      >
        <Switch
          id="ai-description-toggle"
          label="Enable AI-powered description generation for repositories"
          labelOff="AI description generation is disabled"
          isChecked={descriptionEnabled}
          onChange={(_event, checked) => handleToggleDescription(checked)}
          isDisabled={!settings?.credentials_verified}
        />
        <FormHelperText>
          <HelperText>
            <HelperTextItem>
              {!settings?.credentials_verified
                ? 'Configure and verify credentials to enable this feature.'
                : 'When enabled, repository administrators can generate descriptions using AI.'}
            </HelperTextItem>
          </HelperText>
        </FormHelperText>
      </FormGroup>
    </Form>
  );
}
