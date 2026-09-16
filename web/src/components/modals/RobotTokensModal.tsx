import {
  Alert,
  Button,
  ClipboardCopy,
  ClipboardCopyVariant,
  Flex,
  FlexItem,
  MenuToggle,
  MenuToggleElement,
  Select,
  SelectOption,
  Tab,
  TabTitleIcon,
  TabTitleText,
  Tabs,
  Content,
  ContentVariants,
  Checkbox,
  FormGroup,
  Stack,
  StackItem,
} from '@patternfly/react-core';
import {AngleRightIcon, DockerIcon, KeyIcon} from '@patternfly/react-icons';
import {useEffect, useState} from 'react';
import {AlertVariant, useUI} from 'src/contexts/UIContext';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {useOrganizations} from 'src/hooks/UseOrganizations';
import {useRobotToken} from 'src/hooks/useRobotAccounts';
import {addDisplayError} from 'src/resources/ErrorHandling';
import {
  fetchRobotAPIScopes,
  IRobotToken,
  updateRobotAPIScopes,
} from 'src/resources/RobotsResource';
import {OAUTH_SCOPES} from 'src/routes/OrganizationsList/Organization/Tabs/OAuthApplications/types';
import 'src/routes/RepositoriesList/css/RobotAccount.css';

const EmptyRobotToken = {
  name: '',
  created: '',
  last_accessed: '',
  description: '',
  token: '',
  unstructured_metadata: {},
};

const ROBOT_API_SCOPES = Object.fromEntries(
  ['repo:read', 'repo:write', 'repo:admin', 'repo:create'].map((scope) => [
    scope,
    OAUTH_SCOPES[scope],
  ]),
);

export default function RobotTokensModal(props: RobotTokensModalProps) {
  const [activeTabKey, setActiveTabKey] = useState<string | number>(0);
  const [, setLoading] = useState<boolean>(true);
  const [tokenData, setTokenData] = useState<IRobotToken>(EmptyRobotToken);
  const [, setErr] = useState<string[]>();
  const config = useQuayConfig();
  const domain = config?.config.SERVER_HOSTNAME;
  const [secretScopeSelected, setSecretScopeSelected] = useState<string>(
    domain + '/' + props.namespace,
  );
  const [isSecretScopeSelectOpen, setIsSecretScopeSelectOpen] =
    useState<boolean>(false);
  const [apiScopes, setAPIScopes] = useState<string[]>([]);
  const [apiScopesLoaded, setAPIScopesLoaded] = useState(false);
  const [savingAPIScopes, setSavingAPIScopes] = useState(false);
  const {usernames} = useOrganizations();
  const isUserOrganization = usernames.includes(props.namespace);

  useEffect(() => {
    let active = true;
    setAPIScopesLoaded(false);
    setAPIScopes([]);

    fetchRobotAPIScopes(
      props.namespace,
      props.name.split('+').pop() || props.name,
      isUserOrganization,
    )
      .then((scope) => {
        if (active) {
          setAPIScopes(scope ? scope.split(' ') : []);
          setAPIScopesLoaded(true);
        }
      })
      .catch((err) => {
        if (active) {
          setErr([addDisplayError('Unable to fetch robot API scopes', err)]);
        }
      });

    return () => {
      active = false;
    };
  }, [props.namespace, props.name, isUserOrganization]);

  const toggleAPIScope = (scope: string, checked: boolean) => {
    setAPIScopes((current) =>
      checked
        ? [...current, scope]
        : current.filter((selected) => selected !== scope),
    );
  };

  const saveAPIScopes = async () => {
    setSavingAPIScopes(true);
    try {
      const scope = await updateRobotAPIScopes(
        props.namespace,
        props.name.split('+').pop() || props.name,
        apiScopes.join(' '),
        isUserOrganization,
      );
      setAPIScopes(scope ? scope.split(' ') : []);
      addAlert({
        variant: AlertVariant.Success,
        title: 'Successfully updated robot Management API scopes',
      });
    } catch (err) {
      setErr([addDisplayError('Unable to update robot API scopes', err)]);
      addAlert({
        variant: AlertVariant.Failure,
        title: 'Failed to update robot Management API scopes',
      });
    } finally {
      setSavingAPIScopes(false);
    }
  };
  const onToggleClick = () => {
    setIsSecretScopeSelectOpen(!isSecretScopeSelectOpen);
  };
  const onSecretScopeSelect = (
    _event: React.MouseEvent<Element, MouseEvent> | undefined,
    value: string | number | undefined,
  ) => {
    setSecretScopeSelected(value as string);
    setIsSecretScopeSelectOpen(false);
  };

  const {addAlert} = useUI();

  const {regenerateRobotToken} = useRobotToken({
    orgName: props.namespace,
    robotAcct: props.name,
    onSuccess: (result) => {
      setLoading(false);
      setTokenData(result);
    },
    onError: (err) => {
      setErr([addDisplayError('Unable to fetch robot accounts', err)]);
      setLoading(false);
    },
  });

  const getDockerConfig = () => {
    const auths = {};
    const scope = secretScopeSelected;
    auths[scope] = {
      auth: btoa(tokenData.name + ':' + tokenData.token),
      email: '',
    };

    return JSON.stringify({auths: auths}, null, '  ');
  };

  const getEscaped = (val) => {
    let escaped = val.replace(/[^a-zA-Z0-9]/g, '-');
    if (escaped[0] == '-') {
      escaped = escaped.slice(1);
    }
    return escaped;
  };

  const getSuffixedFilename = (suffix) => {
    if (!(tokenData.name || tokenData.token)) {
      return '';
    }

    const prefix = getEscaped(tokenData.name);
    return prefix + '-' + suffix;
  };

  const getKubernetesSecretName = () => {
    if (!(tokenData.name || tokenData.token)) {
      return '';
    }

    return getSuffixedFilename('pull-secret');
  };

  const getKubernetesConfiguration = () => {
    return (
      'apiVersion: v1\n' +
      'kind: Pod\n' +
      'metadata:\n' +
      '  name: somepod\n' +
      '  namespace: all\n' +
      'spec:\n' +
      '  containers:\n' +
      '    - name: web\n' +
      `      image: ${domain}/${props.namespace}/somerepo\n` +
      '  imagePullSecrets:\n' +
      `    - name: ${getKubernetesSecretName()}`
    );
  };

  const getKubernetesContent = () => {
    const dockerConfigJson = getDockerConfig();
    return [
      'apiVersion: v1\n',
      'kind: Secret\n',
      'metadata:\n',
      '  name: ',
      getKubernetesSecretName(),
      '\n',
      'data:\n',
      '  .dockerconfigjson: ',
      btoa(dockerConfigJson),
      '\n',
      'type: kubernetes.io/dockerconfigjson',
    ];
  };

  const onClickRegenerateRobotToken = async () => {
    await regenerateRobotToken({
      namespace: props.namespace,
      robotName: props.name,
    });
  };

  const handleTabClick = (
    _event: React.MouseEvent<unknown> | React.KeyboardEvent | MouseEvent,
    tabIndex: string | number,
  ) => {
    setActiveTabKey(tabIndex);
  };

  const downloadFile = (fileContent, filename) => {
    const blob = new Blob(fileContent, {type: 'text/plain'});
    const element = document.createElement('a');
    element.href = URL.createObjectURL(blob);
    element.download = filename;
    element.click();
  };

  const downloadKubernetesFile = (filename) => {
    const fileContent = getKubernetesContent();
    downloadFile(fileContent, filename);
  };

  const kubesClusterCmd = `kubectl create -f ${props.name.replace(
    '+',
    '-',
  )}-secret.yml --namespace=NAMESPACEHERE`;

  const secretScopeOptions = [
    {value: domain + '/' + props.namespace, label: 'Organization'},
    {value: domain, label: 'Registry'},
  ];

  const secretScopeToggle = (toggleRef: React.Ref<MenuToggleElement>) => (
    <MenuToggle
      id="secret-scope-toggle"
      data-testid="secret-scope-toggle"
      ref={toggleRef}
      onClick={onToggleClick}
      isExpanded={isSecretScopeSelectOpen}
      style={
        {
          width: '200px',
        } as React.CSSProperties
      }
    >
      {
        secretScopeOptions.find(
          (option) => option.value === secretScopeSelected,
        )?.label
      }
    </MenuToggle>
  );

  return (
    <>
      <Tabs activeKey={activeTabKey} onSelect={handleTabClick} role="region">
        <Tab
          eventKey={0}
          title={
            <>
              <TabTitleIcon>
                <KeyIcon />
              </TabTitleIcon>
              <TabTitleText>Robot Account</TabTitleText>
            </>
          }
        >
          <br />
          <>
            <Content>
              <Content component={ContentVariants.h6}>
                Username & Robot account
              </Content>
              <ClipboardCopy hoverTip="Copy" clickTip="Copied" isReadOnly>
                {props.name}
              </ClipboardCopy>
              <ClipboardCopy hoverTip="Copy" clickTip="Copied" isReadOnly>
                {tokenData.token}
              </ClipboardCopy>
            </Content>
            <br />
            <Alert
              title="Note that once you regenerate token, all existing logins of this robot account will become invalid."
              variant="warning"
              isPlain
              isInline
            />
            <Button
              variant="secondary"
              onClick={() => onClickRegenerateRobotToken()}
            >
              Regenerate token now
            </Button>
            <br />
            <br />
            <FormGroup label="Management API scopes" fieldId="robot-api-scopes">
              <Content component={ContentVariants.p}>
                These scopes authorize this robot&apos;s existing token to use
                specific Quay Management API capabilities. The robot must still
                have the underlying Quay permissions required for each
                operation.
              </Content>
              <Stack hasGutter>
                {Object.entries(ROBOT_API_SCOPES).map(
                  ([scopeName, scopeInfo]) => (
                    <StackItem key={scopeName}>
                      <Checkbox
                        id={`robot-api-scope-${scopeName}`}
                        label={scopeInfo.title}
                        description={scopeInfo.description}
                        isChecked={apiScopes.includes(scopeName)}
                        isDisabled={!apiScopesLoaded || savingAPIScopes}
                        onChange={(_event, checked) =>
                          toggleAPIScope(scopeName, checked)
                        }
                        data-testid={`robot-api-scope-${scopeName}`}
                      />
                    </StackItem>
                  ),
                )}
              </Stack>
              <Button
                variant="primary"
                onClick={saveAPIScopes}
                isLoading={savingAPIScopes}
                isDisabled={!apiScopesLoaded || savingAPIScopes}
                data-testid="save-robot-api-scopes"
              >
                Save API scopes
              </Button>
            </FormGroup>
          </>
        </Tab>
        <Tab
          id="kubernetes-tab"
          data-testid="kubernetes-tab"
          eventKey={1}
          title={
            <>
              <TabTitleIcon>
                <img
                  src={require(
                    activeTabKey == 1
                      ? 'src/assets/kubernetes.svg'
                      : 'src/assets/kubernetes-grey.svg',
                  )}
                />
              </TabTitleIcon>
              <TabTitleText>Kubernetes</TabTitleText>
            </>
          }
        >
          <br />
          <Content>
            <Content component={ContentVariants.h6}>
              Step 1: Select the scope of the secret
            </Content>
            <Content component={ContentVariants.p}>
              The Kubernetes runtime can be instructed to use this secret only
              for a specific Quay organization or registry-wide.
            </Content>
            <Flex columnGap={{default: 'columnGapMd'}}>
              <FlexItem>
                <Select
                  id="secret-scope-selector"
                  data-testid="secret-scope-selector"
                  isOpen={isSecretScopeSelectOpen}
                  selected={secretScopeSelected}
                  onSelect={onSecretScopeSelect}
                  onOpenChange={(isOpen) => setIsSecretScopeSelectOpen(isOpen)}
                  toggle={secretScopeToggle}
                  shouldFocusToggleOnSelect
                >
                  {secretScopeOptions.map((option, index) => (
                    <SelectOption key={index} value={option.value}>
                      {option.label}
                    </SelectOption>
                  ))}
                </Select>
              </FlexItem>
              <FlexItem>
                <AngleRightIcon />
              </FlexItem>
              <FlexItem>
                <Content
                  id="secret-scope"
                  data-testid="secret-scope"
                  component={ContentVariants.p}
                >
                  {secretScopeSelected}
                </Content>
              </FlexItem>
            </Flex>
            <Content component={ContentVariants.h6}>
              Step 2: Download secret
            </Content>
            <Content component={ContentVariants.p}>
              Next, download the Kubernetes pull secret for the robot account:
            </Content>
            <ClipboardCopy
              isReadOnly
              isCode
              hoverTip="Copy"
              clickTip="Copied"
              variant={ClipboardCopyVariant.expansion}
              id="step-2"
              data-testid="step-2-secret"
              className="pf-v6-u-mb-sm"
            >
              {getKubernetesContent().join('')}
            </ClipboardCopy>
            <Content component={ContentVariants.p}>
              <Button
                variant="link"
                isInline
                onClick={() =>
                  downloadKubernetesFile(getSuffixedFilename('secret.yml'))
                }
              >
                {'Download ' + getSuffixedFilename('secret.yml')}
              </Button>
            </Content>
            <Content component={ContentVariants.h6}>Step 3: Submit</Content>
            <Content component={ContentVariants.p}>
              Then, submit the secret to the cluster using this command:
            </Content>
            <ClipboardCopy
              hoverTip="Copy"
              clickTip="Copied"
              variant="inline-compact"
              id="step-3"
            >
              {kubesClusterCmd}
            </ClipboardCopy>
            <Content component={ContentVariants.h6}>
              Step 4: Update Kubernetes Configuration
            </Content>
            <Content component={ContentVariants.p}>
              Finally, add a reference to the secret to your Kuberenetes pod
              config via an imagePullSecrets field. For example:
            </Content>
            <ClipboardCopy
              isReadOnly
              isCode
              hoverTip="Copy"
              clickTip="Copied"
              variant={ClipboardCopyVariant.expansion}
              id="step-4"
            >
              {getKubernetesConfiguration()}
            </ClipboardCopy>
          </Content>
        </Tab>
        <Tab
          eventKey={2}
          title={
            <>
              <TabTitleIcon>
                <img
                  src={require(
                    activeTabKey == 2
                      ? 'src/assets/podman.svg'
                      : 'src/assets/podman-grey.svg',
                  )}
                />
              </TabTitleIcon>
              <TabTitleText>Podman</TabTitleText>
            </>
          }
        >
          <br />
          <Content>
            <Content component={ContentVariants.h6}>Podman Login</Content>
            <Content component={ContentVariants.p}>
              Enter the following command on the command line:
            </Content>
            <ClipboardCopy
              hoverTip="Copy"
              clickTip="Copied"
              isReadOnly
              id="podman-login"
            >
              {"podman login -u='" +
                tokenData.name +
                "' -p='" +
                tokenData.token +
                "' " +
                domain}
            </ClipboardCopy>
          </Content>
        </Tab>
        <Tab
          eventKey={3}
          title={
            <>
              <TabTitleIcon>
                <DockerIcon />
              </TabTitleIcon>
              <TabTitleText>Docker Login</TabTitleText>
            </>
          }
        >
          <br />
          <Content>
            <Content component={ContentVariants.h6}>Docker Login</Content>
            <Content component={ContentVariants.p}>
              Enter the following command on the command line:
            </Content>
            <ClipboardCopy
              hoverTip="Copy"
              clickTip="Copied"
              isReadOnly
              id="docker-login"
            >
              {"docker login -u='" +
                tokenData.name +
                "' -p='" +
                tokenData.token +
                "' " +
                domain}
            </ClipboardCopy>
          </Content>
        </Tab>
        <Tab
          id="docker-config-tab"
          data-testid="docker-config-tab"
          eventKey={4}
          title={
            <>
              <TabTitleIcon>
                <DockerIcon />
              </TabTitleIcon>
              <TabTitleText>Docker Configuration</TabTitleText>
            </>
          }
        >
          <br />
          <Content>
            <Content component={ContentVariants.h6}>
              Step 1: Download Docker configuration file
            </Content>
            <Content component={ContentVariants.p}>
              The following is a Docker configuration file containing the
              credentials for this robot account:
            </Content>
            <ClipboardCopy
              isReadOnly
              isCode
              hoverTip="Copy"
              clickTip="Copied"
              variant={ClipboardCopyVariant.expansion}
              id="docker-config-content"
              data-testid="docker-config-content"
              className="pf-v6-u-mb-sm"
            >
              {getDockerConfig()}
            </ClipboardCopy>
            <Content component={ContentVariants.p}>
              <Button
                variant="link"
                isInline
                data-testid="docker-config-download"
                onClick={() =>
                  downloadFile(
                    [getDockerConfig()],
                    getSuffixedFilename('auth.json'),
                  )
                }
              >
                {'Download ' + getSuffixedFilename('auth.json')}
              </Button>
            </Content>
          </Content>
          <br />
          <Alert
            title="Note that once you place this file, any existing credentials will be overwritten."
            variant="warning"
            isPlain
            isInline
          />
          <ClipboardCopy
            hoverTip="Copy"
            clickTip="Copied"
            isReadOnly
            id="docker-config-mv"
          >
            {`mv ${getSuffixedFilename('auth.json')} ~/.docker/config.json`}
          </ClipboardCopy>
        </Tab>
      </Tabs>
    </>
  );
}

interface RobotTokensModalProps {
  namespace: string;
  name: string;
}
