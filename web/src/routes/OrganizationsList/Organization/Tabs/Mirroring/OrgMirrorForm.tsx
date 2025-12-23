import {
  ActionGroup,
  Button,
  Checkbox,
  Flex,
  Form,
  FormGroup,
  FormHelperText,
  FormSelect,
  FormSelectOption,
  HelperText,
  HelperTextItem,
  Spinner,
  TextInput,
} from '@patternfly/react-core';
import {useState, useEffect} from 'react';
import {useFetchRobotAccounts} from 'src/hooks/useRobotAccounts';
import {
  OrgMirrorConfig,
  OrgMirrorConfigResponse,
} from 'src/resources/OrgMirrorResource';
import FilteringConfig, {FilteringType} from './FilteringConfig';

export interface OrgMirrorFormData {
  external_reference: string;
  external_registry_username: string;
  external_registry_password: string;
  internal_robot: string;
  sync_interval: number;
  skopeo_timeout: number;
  is_enabled: boolean;
  verify_tls: boolean;
  filtering_type: FilteringType;
  repo_list: string;
  repo_regex: string;
}

interface OrgMirrorFormProps {
  organizationName: string;
  existingConfig?: OrgMirrorConfigResponse | null;
  onSubmit: (config: OrgMirrorConfig) => Promise<void>;
  onCancel?: () => void;
  onDelete?: () => void;
  isSubmitting?: boolean;
  isDeleting?: boolean;
  submitLabel?: string;
}

const syncIntervalOptions = [
  {value: 3600, label: '1 hour'},
  {value: 21600, label: '6 hours'},
  {value: 43200, label: '12 hours'},
  {value: 86400, label: '1 day'},
  {value: 604800, label: '1 week'},
];

export default function OrgMirrorForm({
  organizationName,
  existingConfig,
  onSubmit,
  onCancel,
  onDelete,
  isSubmitting = false,
  isDeleting = false,
  submitLabel = 'Save',
}: OrgMirrorFormProps) {
  const [formData, setFormData] = useState<OrgMirrorFormData>(() => {
    if (existingConfig) {
      // Parse existing filtering config
      let filteringType: FilteringType = 'NONE';
      let repoList = '';
      let repoRegex = '';

      if (existingConfig.root_rule) {
        filteringType = existingConfig.root_rule.rule_type as FilteringType;
        const ruleValue = existingConfig.root_rule.rule_value;
        if (filteringType === 'REGEX' && typeof ruleValue === 'string') {
          repoRegex = ruleValue;
        } else if (typeof ruleValue === 'object' && ruleValue.repos) {
          repoList = ruleValue.repos.join('\n');
        }
      }

      return {
        external_reference: existingConfig.external_reference || '',
        external_registry_username:
          existingConfig.external_registry_username || '',
        external_registry_password: '',
        internal_robot: existingConfig.internal_robot || '',
        sync_interval: existingConfig.sync_interval || 86400,
        skopeo_timeout: existingConfig.skopeo_timeout || 300,
        is_enabled: existingConfig.is_enabled !== false,
        verify_tls:
          existingConfig.external_registry_config?.verify_tls !== false,
        filtering_type: filteringType,
        repo_list: repoList,
        repo_regex: repoRegex,
      };
    }

    return {
      external_reference: '',
      external_registry_username: '',
      external_registry_password: '',
      internal_robot: '',
      sync_interval: 86400,
      skopeo_timeout: 300,
      is_enabled: true,
      verify_tls: true,
      filtering_type: 'NONE',
      repo_list: '',
      repo_regex: '',
    };
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  const {robots, isLoadingRobots} = useFetchRobotAccounts(
    organizationName,
    false,
    true,
  );

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.external_reference.trim()) {
      newErrors.external_reference = 'Source registry is required';
    }

    if (!formData.internal_robot) {
      newErrors.internal_robot = 'Robot account is required';
    }

    if (formData.filtering_type === 'REGEX' && formData.repo_regex) {
      try {
        new RegExp(formData.repo_regex);
      } catch (e) {
        newErrors.repo_regex = 'Invalid regular expression';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    // Build root_rule based on filtering type
    let root_rule = null;
    if (formData.filtering_type !== 'NONE') {
      if (formData.filtering_type === 'REGEX') {
        root_rule = {
          rule_type: formData.filtering_type,
          rule_value: formData.repo_regex,
        };
      } else {
        const repos = formData.repo_list
          .split('\n')
          .map((r) => r.trim())
          .filter((r) => r.length > 0);
        root_rule = {
          rule_type: formData.filtering_type,
          rule_value: {repos},
        };
      }
    }

    const config: OrgMirrorConfig = {
      external_reference: formData.external_reference.trim(),
      internal_robot: formData.internal_robot,
      sync_interval: formData.sync_interval,
      skopeo_timeout: formData.skopeo_timeout,
      is_enabled: formData.is_enabled,
      external_registry_config: {
        verify_tls: formData.verify_tls,
      },
      root_rule,
    };

    // Only include credentials if provided
    if (formData.external_registry_username) {
      config.external_registry_username = formData.external_registry_username;
    }
    if (formData.external_registry_password) {
      config.external_registry_password = formData.external_registry_password;
    }

    await onSubmit(config);
  };

  const handleFilteringChange = (
    type: FilteringType,
    list: string,
    regex: string,
  ) => {
    setFormData((prev) => ({
      ...prev,
      filtering_type: type,
      repo_list: list,
      repo_regex: regex,
    }));
  };

  return (
    <Form id="org-mirror-form" onSubmit={handleSubmit} maxWidth="70%">
      <FormGroup
        isRequired
        label="Source Registry"
        fieldId="external-reference"
      >
        <TextInput
          isRequired
          type="text"
          id="external-reference"
          data-testid="external-reference-input"
          value={formData.external_reference}
          onChange={(_event, value) =>
            setFormData((prev) => ({...prev, external_reference: value}))
          }
          placeholder="harbor.example.com/project-name"
          validated={errors.external_reference ? 'error' : 'default'}
          isDisabled={!!existingConfig}
        />
        <FormHelperText>
          <HelperText>
            <HelperTextItem>
              The source registry and project/organization to mirror from (e.g.,
              harbor.example.com/my-project or quay.io/org-name)
            </HelperTextItem>
          </HelperText>
        </FormHelperText>
        {errors.external_reference && (
          <HelperText>
            <HelperTextItem variant="error">
              {errors.external_reference}
            </HelperTextItem>
          </HelperText>
        )}
      </FormGroup>

      <FormGroup isRequired label="Robot Account" fieldId="internal-robot">
        {isLoadingRobots ? (
          <Spinner size="md" />
        ) : (
          <FormSelect
            id="internal-robot"
            data-testid="robot-account-select"
            value={formData.internal_robot}
            onChange={(_event, value) =>
              setFormData((prev) => ({...prev, internal_robot: value}))
            }
            validated={errors.internal_robot ? 'error' : 'default'}
            isDisabled={!!existingConfig}
          >
            <FormSelectOption value="" label="Select a robot account..." />
            {robots?.map((robot) => (
              <FormSelectOption
                key={robot.name}
                value={robot.name}
                label={robot.name}
              />
            ))}
          </FormSelect>
        )}
        <FormHelperText>
          <HelperText>
            <HelperTextItem>
              Robot account used to create mirrored repositories and pull images
            </HelperTextItem>
          </HelperText>
        </FormHelperText>
        {errors.internal_robot && (
          <HelperText>
            <HelperTextItem variant="error">
              {errors.internal_robot}
            </HelperTextItem>
          </HelperText>
        )}
      </FormGroup>

      <FormGroup label="Source Registry Username" fieldId="registry-username">
        <TextInput
          type="text"
          id="registry-username"
          data-testid="registry-username-input"
          value={formData.external_registry_username}
          onChange={(_event, value) =>
            setFormData((prev) => ({
              ...prev,
              external_registry_username: value,
            }))
          }
          placeholder="Username or token"
        />
        <FormHelperText>
          <HelperText>
            <HelperTextItem>
              Username for authenticating with the source registry (optional for
              public registries)
            </HelperTextItem>
          </HelperText>
        </FormHelperText>
      </FormGroup>

      <FormGroup label="Source Registry Password" fieldId="registry-password">
        <TextInput
          type="password"
          id="registry-password"
          data-testid="registry-password-input"
          value={formData.external_registry_password}
          onChange={(_event, value) =>
            setFormData((prev) => ({
              ...prev,
              external_registry_password: value,
            }))
          }
          placeholder={existingConfig ? '(unchanged)' : 'Password or token'}
        />
        <FormHelperText>
          <HelperText>
            <HelperTextItem>
              Password for authenticating with the source registry
            </HelperTextItem>
          </HelperText>
        </FormHelperText>
      </FormGroup>

      <FormGroup isRequired label="Sync Interval" fieldId="sync-interval">
        <FormSelect
          id="sync-interval"
          data-testid="sync-interval-select"
          value={formData.sync_interval}
          onChange={(_event, value) =>
            setFormData((prev) => ({...prev, sync_interval: Number(value)}))
          }
        >
          {syncIntervalOptions.map((option) => (
            <FormSelectOption
              key={option.value}
              value={option.value}
              label={option.label}
            />
          ))}
        </FormSelect>
        <FormHelperText>
          <HelperText>
            <HelperTextItem>
              How often to check for new images in the source registry
            </HelperTextItem>
          </HelperText>
        </FormHelperText>
      </FormGroup>

      <FormGroup label="Skopeo Timeout" fieldId="skopeo-timeout">
        <TextInput
          type="number"
          id="skopeo-timeout"
          data-testid="skopeo-timeout-input"
          value={formData.skopeo_timeout}
          onChange={(_event, value) =>
            setFormData((prev) => ({...prev, skopeo_timeout: Number(value)}))
          }
          min={0}
        />
        <FormHelperText>
          <HelperText>
            <HelperTextItem>
              Timeout in seconds for skopeo operations (default: 300)
            </HelperTextItem>
          </HelperText>
        </FormHelperText>
      </FormGroup>

      <FilteringConfig
        filteringType={formData.filtering_type}
        repoList={formData.repo_list}
        repoRegex={formData.repo_regex}
        onChange={handleFilteringChange}
        errors={errors}
      />

      <FormGroup fieldId="settings-group" label="Settings">
        <Checkbox
          label="Enable organization mirror"
          isChecked={formData.is_enabled}
          onChange={(_event, checked) =>
            setFormData((prev) => ({...prev, is_enabled: checked}))
          }
          id="is-enabled-checkbox"
          data-testid="is-enabled-checkbox"
        />
        <Checkbox
          label="Verify TLS certificates"
          isChecked={formData.verify_tls}
          onChange={(_event, checked) =>
            setFormData((prev) => ({...prev, verify_tls: checked}))
          }
          id="verify-tls-checkbox"
          data-testid="verify-tls-checkbox"
        />
      </FormGroup>

      <ActionGroup>
        <Flex justifyContent={{default: 'justifyContentFlexEnd'}} width="100%">
          <Button
            variant="primary"
            type="submit"
            data-testid="submit-btn"
            isLoading={isSubmitting}
            isDisabled={isSubmitting || isDeleting}
          >
            {submitLabel}
          </Button>
          {onDelete && (
            <Button
              variant="danger"
              data-testid="delete-btn"
              onClick={onDelete}
              isLoading={isDeleting}
              isDisabled={isSubmitting || isDeleting}
            >
              Delete
            </Button>
          )}
          {onCancel && (
            <Button
              variant="link"
              data-testid="cancel-btn"
              onClick={onCancel}
              isDisabled={isSubmitting || isDeleting}
            >
              Cancel
            </Button>
          )}
        </Flex>
      </ActionGroup>
    </Form>
  );
}
