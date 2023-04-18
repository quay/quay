import {useEffect, useState} from 'react';
import {
  Tabs,
  Tab,
  TextContent,
  Text,
  TextVariants,
  ClipboardCopy,
  ClipboardCopyVariant,
  ExpandableSection,
  ExpandableSectionToggle,
  TextArea,
  Grid,
  GridItem,
  TabTitleIcon,
  TabTitleText,
  Alert,
  Button,
} from '@patternfly/react-core';
import {useRobotToken} from 'src/hooks/useRobotToken';
import {addDisplayError} from 'src/resources/ErrorHandling';
import {IRobot, IRobotToken} from 'src/resources/RobotsResource';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {DockerIcon, KeyIcon} from '@patternfly/react-icons';
import 'src/routes/RepositoriesList/css/RobotAccount.css';
import {Buffer} from 'buffer';

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
  const [isSecretExpanded, setSecretExpanded] = useState(false);
  const [loading, setLoading] = useState<boolean>(true);
  const [tokenData, setTokenData] = useState<IRobotToken>(EmptyRobotToken);
  const [err, setErr] = useState<string[]>();
  const config = useQuayConfig();
  const domain = config?.config.SERVER_HOSTNAME;

  const {robotAccountToken, regenerateRobotToken} = useRobotToken({
    orgName: props.namespace,
    robName: props.robotAccount.name,
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
    auths[domain] = {
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
      robotName: props.robotAccount.name,
    });
  };

  const handleTabClick = (
    event: React.MouseEvent<any> | React.KeyboardEvent | MouseEvent,
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

  const onViewToggle = (isSecretExpanded: boolean) => {
    setSecretExpanded(isSecretExpanded);
  };

  const kubesClusterCmd = `kubectl create -f ${props.robotAccount.name.replace(
    '+',
    '-',
  )}-secret.yml --namespace=NAMESPACEHERE`;

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
                {props.robotAccount.name}
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
          eventKey={1}
          title={
            <>
              <TabTitleIcon>
                <img
                  src={require(activeTabKey == 1
                    ? 'src/assets/kubernetes.svg'
                    : 'src/assets/kubernetes-grey.svg')}
                />
              </TabTitleIcon>
              <TabTitleText>Kubernetes</TabTitleText>
            </>
          }
        >
          <br />
          <TextContent>
            <Text component={TextVariants.h6}>Step 1: Download secret</Text>
            <Text component={TextVariants.p}>
              First, download the Kubernetes pull secret for the robot account:
            </Text>
            <Grid>
              <GridItem span={6} rowSpan={1}>
                <a
                  onClick={() =>
                    downloadKubernetesFile(getSuffixedFilename('secret.yml'))
                  }
                >
                  {'Download ' + getSuffixedFilename('secret.yml')}
                </a>
              </GridItem>
              <GridItem rowSpan={1} span={6}>
                <ExpandableSectionToggle
                  onToggle={onViewToggle}
                  isExpanded={isSecretExpanded}
                  contentId="view-kube-file"
                >
                  {isSecretExpanded
                    ? 'Show less'
                    : 'View ' + getSuffixedFilename('secret.yml')}
                </ExpandableSectionToggle>
              </GridItem>
            </Grid>
            <ExpandableSection
              isDetached
              isExpanded={isSecretExpanded}
              contentId="view-kube-file"
            >
              <TextArea
                value={getKubernetesContent().join('')}
                isReadOnly={true}
                autoResize={true}
                className="text-area-height"
                id="expandable-kube-content"
              />
            </ExpandableSection>
            <Text component={TextVariants.h6}>Step 2: Submit</Text>
            <Text component={TextVariants.p}>
              Second, submit the secret to the cluster using this command:
            </Text>
            <ClipboardCopy
              hoverTip="Copy"
              clickTip="Copied"
              variant="inline-compact"
              id="step-2"
            >
              {kubesClusterCmd}
            </ClipboardCopy>
            <Text component={TextVariants.h6}>
              Step 3: Update Kubernetes Configuration
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
                  src={require(activeTabKey == 2
                    ? 'src/assets/podman.svg'
                    : 'src/assets/podman-grey.svg')}
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
              <TabTitleText>Docker configuration</TabTitleText>
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
  robotAccount: IRobot;
}
