import {
  Modal,
  ModalVariant,
  Button,
  Form,
  FormGroup,
  TextInput,
  FormHelperText,
  HelperText,
  HelperTextItem,
  Checkbox,
  Radio,
} from '@patternfly/react-core';
import ExclamationCircleIcon from '@patternfly/react-icons/dist/esm/icons/exclamation-circle-icon';
import './css/Organizations.scss';
import {isValidEmail} from 'src/libs/utils';
import {useState} from 'react';
import FormError from 'src/components/errors/FormError';
import {addDisplayError} from 'src/resources/ErrorHandling';
import {useCreateOrganization} from 'src/hooks/UseCreateOrganization';
import Conditional from 'src/components/empty/Conditional';
import {tagExpirationInSecsForProxyCache} from './Organization/Tabs/Settings/ProxyCacheConfig';
import {
  IProxyCacheConfig,
  useCreateProxyCacheConfig,
  useValidateProxyCacheConfig,
} from 'src/hooks/UseProxyCache';
import {useAlerts} from 'src/hooks/UseAlerts';
import {AlertVariant} from 'src/atoms/AlertState';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';

interface Validation {
  message: string;
  isValid: boolean;
  type: 'default' | 'error' | 'warning';
}

const defaultMessage: Validation = {
  message:
    'This will also be the namespace for your repositories. Must be alphanumeric, all lowercase, at least 2 characters long and at most 255 characters long',
  isValid: true,
  type: 'default',
};

export const CreateOrganizationModal = (
  props: CreateOrganizationModalProps,
): JSX.Element => {
  const [organizationName, setOrganizationName] = useState('');
  const [organizationEmail, setOrganizationEmail] = useState('');
  const [invalidEmailFlag, setInvalidEmailFlag] = useState(false);
  const [validation, setValidation] = useState<Validation>(defaultMessage);
  const [err, setErr] = useState<string>();
  const [proxyOrgCheck, setProxyOrgCheck] = useState(false);
  const quayConfig = useQuayConfig();

  const defaultProxyCacheConfig = {
    upstream_registry: '',
    expiration_s: tagExpirationInSecsForProxyCache,
    insecure: false,
  };

  const [proxyCacheConfig, setProxyCacheConfig] = useState<IProxyCacheConfig>(
    defaultProxyCacheConfig,
  );
  const {addAlert} = useAlerts();

  const {createProxyCacheConfigMutation} = useCreateProxyCacheConfig({
    onSuccess: () => {
      addAlert({
        variant: AlertVariant.Success,
        title: `Successfully configured proxy cache for ${organizationName}`,
      });
    },
    onError: (err) => {
      addAlert({
        variant: AlertVariant.Failure,
        title: err,
      });
    },
  });

  const {proxyCacheConfigValidation} = useValidateProxyCacheConfig(
    proxyCacheConfig,
    {
      onSuccess: (response) => {
        if (response === 'Valid' || response === 'Anonymous') {
          createProxyCacheConfigMutation(proxyCacheConfig);
        }
      },
      onError: (err) => {
        addAlert({
          variant: AlertVariant.Failure,
          title: err,
        });
      },
    },
  );

  const {createOrganization} = useCreateOrganization({
    onSuccess: (response) => {
      if (response === 'Created') {
        addAlert({
          variant: AlertVariant.Success,
          title: `Successfully created ${organizationName} organization`,
        });
        if (proxyOrgCheck) {
          proxyCacheConfigValidation();
        }
        props.handleModalToggle();
      }
    },
    onError: (err) => {
      setErr(addDisplayError('Unable to create organization', err));
    },
  });

  const handleNameInputChange = (value: string) => {
    const regex = /^([a-z0-9]+(?:[._-][a-z0-9]+)*)$/;
    if (!regex.test(value) || value.length >= 256 || value.length < 2) {
      setValidation({
        message:
          'Must be alphanumeric, all lowercase, at least 2 characters long and at most 255 characters long',
        isValid: false,
        type: 'error',
      });
    } else if (value.length > 30 || value.length < 4) {
      setValidation({
        message:
          'Namespaces less than 4 or more than 30 characters are only compatible with Docker 1.6+',
        isValid: true,
        type: 'warning',
      });
    } else if (value.includes('.') || value.includes('-')) {
      setValidation({
        message:
          'Namespaces with dashes or dots are only compatible with Docker 1.9+',
        isValid: true,
        type: 'warning',
      });
    } else {
      setValidation(defaultMessage);
    }
    setOrganizationName(value);
    setProxyCacheConfig((prevConfig) => ({
      ...prevConfig,
      org_name: value,
    }));
  };

  const handleEmailInputChange = (value: string) => {
    setOrganizationEmail(value);
  };

  const createOrganizationHandler = async () => {
    await createOrganization(organizationName, organizationEmail);
  };

  const onInputBlur = () => {
    if (organizationEmail.length !== 0) {
      isValidEmail(organizationEmail)
        ? setInvalidEmailFlag(false)
        : setInvalidEmailFlag(true);
    } else {
      return;
    }
  };

  return (
    <Modal
      title="Create Organization"
      variant={ModalVariant.large}
      isOpen={props.isModalOpen}
      onClose={props.handleModalToggle}
      actions={[
        <Button
          id="create-org-confirm"
          data-testid="create-org-confirm"
          key="confirm"
          variant="primary"
          onClick={createOrganizationHandler}
          form="modal-with-form-form"
          isDisabled={
            invalidEmailFlag || !organizationName || !validation.isValid
          }
        >
          Create
        </Button>,
        <Button
          id="create-org-cancel"
          key="cancel"
          variant="link"
          onClick={props.handleModalToggle}
        >
          Cancel
        </Button>,
      ]}
    >
      <FormError message={err} setErr={setErr} />
      <Form id="create-org-modal" isWidthLimited>
        <FormGroup
          isInline
          label="Organization Name"
          isRequired
          fieldId="create-org-name"
        >
          <TextInput
            isRequired
            type="text"
            id="create-org-name-input"
            value={organizationName}
            onChange={(_event, value) => handleNameInputChange(value)}
            validated={validation.type}
          />

          <FormHelperText>
            <HelperText>
              <HelperTextItem
                variant={validation.type}
                {...(validation.type === 'error' && {
                  icon: <ExclamationCircleIcon />,
                })}
              >
                {validation.message}
              </HelperTextItem>
            </HelperText>
          </FormHelperText>
        </FormGroup>
        <FormGroup label="Organization Email" fieldId="create-org-email">
          <TextInput
            type="email"
            id="create-org-email-input"
            name="create-org-email-input"
            value={organizationEmail}
            onChange={(_event, value) => handleEmailInputChange(value)}
            validated={invalidEmailFlag ? 'error' : 'default'}
            onBlur={onInputBlur}
          />

          <FormHelperText>
            <HelperText>
              {invalidEmailFlag ? (
                <HelperTextItem
                  variant="error"
                  icon={<ExclamationCircleIcon />}
                >
                  Enter a valid email: email@provider.com
                </HelperTextItem>
              ) : (
                <HelperTextItem>
                  {"This address must be different from your account's email"}
                </HelperTextItem>
              )}
            </HelperText>
          </FormHelperText>
        </FormGroup>

        <Conditional if={quayConfig?.features?.PROXY_CACHE}>
          <FormGroup
            isInline
            label="Is this a proxy cache organization?"
            fieldId="radio-proxy-cache"
          >
            <Radio
              isChecked={proxyOrgCheck}
              name="Yes"
              onChange={() => setProxyOrgCheck(true)}
              label="Yes"
              id="radio-controlled-yes"
              data-testid="radio-controlled-yes"
            />
            <Radio
              isChecked={!proxyOrgCheck}
              name="No"
              onChange={() => setProxyOrgCheck(false)}
              label="No"
              id="radio-controlled-no"
              data-testid="radio-controlled-no"
            />
          </FormGroup>
          <Conditional if={proxyOrgCheck}>
            <FormGroup
              isInline
              label="Remote Registry"
              fieldId="form-remote-registry"
            >
              <TextInput
                type="text"
                id="form-name"
                data-testid="remote-registry-input"
                value={proxyCacheConfig?.upstream_registry || ''}
                onChange={(_event, registryName) =>
                  setProxyCacheConfig((prevConfig) => ({
                    ...prevConfig,
                    upstream_registry: registryName,
                  }))
                }
              />

              <FormHelperText>
                <HelperText>
                  <HelperTextItem>
                    Remote registry that is to be cached. (Eg: For docker hub,
                    docker.io, docker.io/library)
                  </HelperTextItem>
                </HelperText>
              </FormHelperText>
            </FormGroup>

            <FormGroup
              isInline
              label="Remote Registry username"
              fieldId="form-username"
            >
              <TextInput
                type="text"
                id="remote-registry-username"
                data-testid="remote-registry-username"
                value={proxyCacheConfig?.upstream_registry_username || ''}
                onChange={(_event, registryUsername) =>
                  setProxyCacheConfig((prevConfig) => ({
                    ...prevConfig,
                    upstream_registry_username: registryUsername,
                  }))
                }
              />

              <FormHelperText>
                <HelperText>
                  <HelperTextItem>
                    Username for authenticating into the entered remote
                    registry. For anonymous pulls from the upstream, leave this
                    empty.
                  </HelperTextItem>
                </HelperText>
              </FormHelperText>
            </FormGroup>

            <FormGroup
              isInline
              label="Remote Registry password"
              fieldId="form-password"
            >
              <TextInput
                type="password"
                id="remote-registry-password"
                data-testid="remote-registry-password"
                value={proxyCacheConfig?.upstream_registry_password || ''}
                onChange={(_event, registryPass) =>
                  setProxyCacheConfig((prevConfig) => ({
                    ...prevConfig,
                    upstream_registry_password: registryPass,
                  }))
                }
              />

              <FormHelperText>
                <HelperText>
                  <HelperTextItem>
                    Password for authenticating into the entered remote
                    registry. For anonymous pulls from the upstream, leave this
                    empty.{' '}
                  </HelperTextItem>
                </HelperText>
              </FormHelperText>
            </FormGroup>

            <FormGroup isInline label="Expiration" fieldId="form-username">
              <TextInput
                type="text"
                id="remote-registry-expiration"
                data-testid="remote-registry-expiration"
                value={proxyCacheConfig?.expiration_s}
                placeholder={tagExpirationInSecsForProxyCache.toString()}
                onChange={(_event, inputSecs) =>
                  setProxyCacheConfig((prevConfig) => ({
                    ...prevConfig,
                    expiration_s: Number(inputSecs),
                  }))
                }
              />

              <FormHelperText>
                <HelperText>
                  <HelperTextItem>
                    Default tag expiration for cached images, in seconds. This
                    value is refreshed on every pull. Default is 86400 i.e, 24
                    hours.{' '}
                  </HelperTextItem>
                </HelperText>
              </FormHelperText>
            </FormGroup>

            <FormGroup isInline label="Insecure" fieldId="form-insecure">
              <Checkbox
                label="http"
                isChecked={proxyCacheConfig?.insecure}
                onChange={(e, checked) =>
                  setProxyCacheConfig((prevConfig) => ({
                    ...prevConfig,
                    insecure: checked,
                  }))
                }
                id="controlled-check-2"
                data-testid="remote-registry-insecure"
              />
              <FormHelperText>
                <HelperText>
                  <HelperTextItem>
                    If set, http (unsecure protocol) will be used. If not set,
                    https (secure protocol) will be used to request the remote
                    registry.
                  </HelperTextItem>
                </HelperText>
              </FormHelperText>
            </FormGroup>
          </Conditional>
        </Conditional>
      </Form>
    </Modal>
  );
};

type CreateOrganizationModalProps = {
  isModalOpen: boolean;
  handleModalToggle?: () => void;
};
