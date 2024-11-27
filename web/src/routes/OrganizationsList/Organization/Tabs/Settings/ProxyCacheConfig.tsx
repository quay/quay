import {
  ActionGroup,
  Button,
  Checkbox,
  Flex,
  Form,
  FormGroup,
  FormHelperText,
  HelperText,
  HelperTextItem,
  Spinner,
  TextInput,
} from '@patternfly/react-core';
import {useEffect, useState} from 'react';
import {AlertVariant} from 'src/atoms/AlertState';
import {useAlerts} from 'src/hooks/UseAlerts';
import {
  IProxyCacheConfig,
  useCreateProxyCacheConfig,
  useDeleteProxyCacheConfig,
  useFetchProxyCacheConfig,
  useValidateProxyCacheConfig,
} from 'src/hooks/UseProxyCache';
import Alerts from 'src/routes/Alerts';

type ProxyCacheConfigProps = {
  organizationName: string;
  isUser: boolean;
};

const tagExpirationInSecsForProxyCache = 86400;

export const ProxyCacheConfig = (props: ProxyCacheConfigProps) => {
  const defaultProxyCacheConfig = {
    upstream_registry: '',
    expiration_s: tagExpirationInSecsForProxyCache,
    insecure: false,
    org_name: props.organizationName,
  };

  const [proxyCacheConfig, setProxyCacheConfig] = useState<IProxyCacheConfig>(
    defaultProxyCacheConfig,
  );
  const {addAlert, clearAllAlerts} = useAlerts();

  const {fetchedProxyCacheConfig, isLoadingProxyCacheConfig} =
    useFetchProxyCacheConfig(props.organizationName);

  useEffect(() => {
    if (fetchedProxyCacheConfig) {
      // only set values that are fetched
      setProxyCacheConfig((prevConfig) => ({
        ...prevConfig,
        upstream_registry: fetchedProxyCacheConfig.upstream_registry,
        expiration_s:
          fetchedProxyCacheConfig.expiration_s ||
          tagExpirationInSecsForProxyCache,
        insecure: fetchedProxyCacheConfig.insecure || false,
      }));
    } else {
      // reset the config if there's no fetchedProxyCacheConfig data
      setProxyCacheConfig(defaultProxyCacheConfig);
    }
  }, [fetchedProxyCacheConfig, props.organizationName]);

  const {createProxyCacheConfigMutation} = useCreateProxyCacheConfig({
    onSuccess: () => {
      addAlert({
        variant: AlertVariant.Success,
        title: `Successfully configured proxy cache`,
      });
    },
    onError: (err) => {
      addAlert({
        variant: AlertVariant.Failure,
        title: err,
      });
    },
  });

  useEffect(() => {
    // clear alerts when switching tabs
    return () => {
      clearAllAlerts();
    };
  }, []);

  const {proxyCacheConfigValidation} = useValidateProxyCacheConfig(
    proxyCacheConfig,
    {
      onSuccess: (response) => {
        if (response === 'Valid' || response === 'Anonymous') {
          createProxyCacheConfigMutation(proxyCacheConfig);
          setProxyCacheConfig(proxyCacheConfig);
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

  const {deleteProxyCacheConfigMutation} = useDeleteProxyCacheConfig(
    props.organizationName,
    {
      onSuccess: () => {
        addAlert({
          variant: AlertVariant.Success,
          title: 'Successfully deleted proxy cache configuration',
        });
      },
      onError: (err) => {
        addAlert({
          variant: AlertVariant.Failure,
          title: err,
        });
      },
    },
  );

  const handleRemoteRegistryInput = (registryName: string) => {
    setProxyCacheConfig((prevConfig) => ({
      ...prevConfig,
      upstream_registry: registryName,
    }));
  };

  const handleRemoteRegistryUsername = (registryUsername: string) => {
    setProxyCacheConfig((prevConfig) => ({
      ...prevConfig,
      upstream_registry_username: registryUsername,
    }));
  };

  const handleRemoteRegistryPassword = (registryPass: string) => {
    setProxyCacheConfig((prevConfig) => ({
      ...prevConfig,
      upstream_registry_password: registryPass,
    }));
  };

  const handleRemoteRegistryExpiration = (expiration: string) => {
    setProxyCacheConfig((prevConfig) => ({
      ...prevConfig,
      expiration_s: Number(expiration),
    }));
  };

  const handleInsecureProtocol = (e, checked: boolean) => {
    setProxyCacheConfig((prevConfig) => ({
      ...prevConfig,
      insecure: checked,
    }));
  };

  if (isLoadingProxyCacheConfig) {
    return <Spinner size="md" />;
  }

  return (
    <Form id="form-form" maxWidth="70%">
      <FormGroup
        isInline
        label="Remote Registry"
        fieldId="form-remote-registry"
      >
        <TextInput
          isDisabled={!!fetchedProxyCacheConfig?.upstream_registry}
          type="text"
          id="form-name"
          data-testid="remote-registry-input"
          value={proxyCacheConfig?.upstream_registry || ''}
          onChange={(_event, registryName) =>
            handleRemoteRegistryInput(registryName)
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
          isDisabled={!!fetchedProxyCacheConfig?.upstream_registry_username}
          type="text"
          id="remote-registry-username"
          data-testid="remote-registry-username"
          value={proxyCacheConfig?.upstream_registry_username || ''}
          onChange={(_event, registryUsername) =>
            handleRemoteRegistryUsername(registryUsername)
          }
        />

        <FormHelperText>
          <HelperText>
            <HelperTextItem>
              Username for authenticating into the entered remote registry. For
              anonymous pulls from the upstream, leave this empty.
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
          isDisabled={!!fetchedProxyCacheConfig?.upstream_registry_password}
          type="password"
          id="remote-registry-password"
          data-testid="remote-registry-password"
          value={proxyCacheConfig?.upstream_registry_password || ''}
          onChange={(_event, password) =>
            handleRemoteRegistryPassword(password)
          }
        />

        <FormHelperText>
          <HelperText>
            <HelperTextItem>
              Password for authenticating into the entered remote registry. For
              anonymous pulls from the upstream, leave this empty.{' '}
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
            handleRemoteRegistryExpiration(inputSecs)
          }
        />

        <FormHelperText>
          <HelperText>
            <HelperTextItem>
              Default tag expiration for cached images, in seconds. This value
              is refreshed on every pull. Default is 86400 i.e, 24 hours.{' '}
            </HelperTextItem>
          </HelperText>
        </FormHelperText>
      </FormGroup>

      <FormGroup isInline label="Insecure" fieldId="form-insecure">
        <Checkbox
          label="http"
          isChecked={proxyCacheConfig?.insecure}
          onChange={handleInsecureProtocol}
          id="controlled-check-2"
          data-testid="remote-registry-insecure"
        />
        <FormHelperText>
          <HelperText>
            <HelperTextItem>
              If set, http (unsecure protocol) will be used. If not set, https
              (secure protocol) will be used to request the remote registry.
            </HelperTextItem>
          </HelperText>
        </FormHelperText>
      </FormGroup>

      <ActionGroup>
        <Flex
          justifyContent={{default: 'justifyContentFlexEnd'}}
          width={'100%'}
        >
          <Button
            id="save-proxy-cache"
            data-testid="save-proxy-cache-btn"
            variant="primary"
            type="submit"
            onClick={(event) => {
              event.preventDefault();
              proxyCacheConfigValidation();
            }}
            isDisabled={
              !proxyCacheConfig?.upstream_registry ||
              !!fetchedProxyCacheConfig?.upstream_registry
            }
          >
            Save
          </Button>

          <Button
            isDisabled={!fetchedProxyCacheConfig?.upstream_registry}
            id="delete-proxy-cache"
            data-testid="delete-proxy-cache-btn"
            variant="danger"
            type="submit"
            onClick={(event) => {
              event.preventDefault();
              deleteProxyCacheConfigMutation();
            }}
          >
            Delete
          </Button>
        </Flex>
      </ActionGroup>
      <Alerts />
    </Form>
  );
};
