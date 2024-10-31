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
  Text,
  TextContent,
  TextVariants,
} from '@patternfly/react-core';
import {AngleRightIcon, DockerIcon, KeyIcon} from '@patternfly/react-icons';
import {Buffer} from 'buffer';
import {useState} from 'react';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {useRobotToken} from 'src/hooks/useRobotAccounts';
import {addDisplayError} from 'src/resources/ErrorHandling';
import {IRobotToken} from 'src/resources/RobotsResource';
import 'src/routes/RepositoriesList/css/RobotAccount.css';

const EmptyRobotToken = {
  name: '',
  created: '',
  last_accessed: '',
  description: '',
  token: '',
  unstructured_metadata: {},
};

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
      auth: Buffer.from(tokenData.name + ':' + tokenData.token).toString(
        'base64',
      ),
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
      Buffer.from(dockerConfigJson).toString('base64'),
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
            <TextContent>
              <Text component={TextVariants.h6}>Username & Robot account</Text>
              <ClipboardCopy hoverTip="Copy" clickTip="Copied" isReadOnly>
                {props.name}
              </ClipboardCopy>
              <ClipboardCopy hoverTip="Copy" clickTip="Copied" isReadOnly>
                {tokenData.token}
              </ClipboardCopy>
              <Text component={TextVariants.h2}>Username & Robot account</Text>
            </TextContent>
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
          </>
        </Tab>
        <Tab
          id="kubernetes-tab"
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
          <TextContent>
            <Text component={TextVariants.h6}>
              Step 1: Select the scope of the secret
            </Text>
            <Text component={TextVariants.p}>
              The Kubernetes runtime can be instructed to use this secret only
              for a specific Quay organization or registry-wide.
            </Text>
            <Flex columnGap={{default: 'columnGapMd'}}>
              <FlexItem>
                <Select
                  id="secret-scope-selector"
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
                <Text id="secret-scope" component={TextVariants.p}>
                  {secretScopeSelected}
                </Text>
              </FlexItem>
            </Flex>
            <Text component={TextVariants.h6}>Step 2: Download secret</Text>
            <Text component={TextVariants.p}>
              Next, download the Kubernetes pull secret for the robot account:
            </Text>
            <ClipboardCopy
              isReadOnly
              isCode
              hoverTip="Copy"
              clickTip="Copied"
              variant={ClipboardCopyVariant.expansion}
              id="step-2"
              className="pf-v5-u-mb-sm"
            >
              {getKubernetesContent().join('')}
            </ClipboardCopy>
            <Text component={TextVariants.p}>
              <a
                onClick={() =>
                  downloadKubernetesFile(getSuffixedFilename('secret.yml'))
                }
              >
                {'Download ' + getSuffixedFilename('secret.yml')}
              </a>
            </Text>
            <Text component={TextVariants.h6}>Step 3: Submit</Text>
            <Text component={TextVariants.p}>
              Then, submit the secret to the cluster using this command:
            </Text>
            <ClipboardCopy
              hoverTip="Copy"
              clickTip="Copied"
              variant="inline-compact"
              id="step-3"
            >
              {kubesClusterCmd}
            </ClipboardCopy>
            <Text component={TextVariants.h6}>
              Step 4: Update Kubernetes Configuration
            </Text>
            <Text component={TextVariants.p}>
              Finally, add a reference to the secret to your Kuberenetes pod
              config via an imagePullSecrets field. For example:
            </Text>
            <ClipboardCopy
              isReadOnly
              isCode
              hoverTip="Copy"
              clickTip="Copied"
              variant={ClipboardCopyVariant.expansion}
              id="step-3"
            >
              {getKubernetesConfiguration()}
            </ClipboardCopy>
          </TextContent>
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
          <TextContent>
            <Text component={TextVariants.h6}>Podman Login</Text>
            <Text component={TextVariants.p}>
              Enter the following command on the command line:
            </Text>
            <ClipboardCopy
              hoverTip="Copy"
              clickTip="Copied"
              isReadOnly
              id="podman-login"
            >
              {'podman login -u="' +
                tokenData.name +
                '" -p="' +
                tokenData.token +
                '" ' +
                domain}
            </ClipboardCopy>
          </TextContent>
        </Tab>
        <Tab
          eventKey={3}
          title={
            <>
              <TabTitleIcon>
                <DockerIcon />
              </TabTitleIcon>
              <TabTitleText>Docker</TabTitleText>
            </>
          }
        >
          <br />
          <TextContent>
            <Text component={TextVariants.h6}>Docker Login</Text>
            <Text component={TextVariants.p}>
              Enter the following command on the command line:
            </Text>
            <ClipboardCopy
              hoverTip="Copy"
              clickTip="Copied"
              isReadOnly
              id="docker login"
            >
              {'docker login -u="' +
                tokenData.name +
                '" -p="' +
                tokenData.token +
                '" ' +
                domain}
            </ClipboardCopy>
          </TextContent>
        </Tab>
      </Tabs>
    </>
  );
}

interface RobotTokensModalProps {
  namespace: string;
  name: string;
}
