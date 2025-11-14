import {useMemo, useState} from 'react';
import {
  Alert,
  Modal,
  ModalVariant,
  Button,
  Form,
  FormGroup,
  ClipboardCopy,
  Tabs,
  Tab,
  TabTitleText,
  CodeBlock,
  CodeBlockCode,
  Text,
} from '@patternfly/react-core';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';

export interface Credentials {
  username: string;
  password: string;
  title: string;
}

export type CredentialsType = 'token' | 'encrypted-password';

interface CredentialsModalProps {
  isOpen: boolean;
  onClose: () => void;
  credentials: Credentials;
  type: CredentialsType;
  isNewlyCreated?: boolean;
}

export default function CredentialsModal({
  isOpen,
  onClose,
  credentials,
  type,
  isNewlyCreated = false,
}: CredentialsModalProps) {
  const [activeTabKey, setActiveTabKey] = useState<string | number>(0);
  const quayConfig = useQuayConfig();

  const getServerHostname = () => {
    return quayConfig?.config?.SERVER_HOSTNAME || window.location.host;
  };

  const getContainerLoginCommand = (runtime: 'docker' | 'podman') => {
    return `${runtime} login -u='${credentials.username}' -p='${
      credentials.password
    }' ${getServerHostname()}`;
  };

  const kubernetesYaml = useMemo(() => {
    const hostname = getServerHostname();
    const dockerConfigJson = {
      auths: {
        [hostname]: {
          auth: btoa(`${credentials.username}:${credentials.password}`),
          email: '',
        },
      },
    };

    return `apiVersion: v1
kind: Secret
metadata:
  name: ${credentials.title}-pull-secret
data:
  .dockerconfigjson: ${btoa(JSON.stringify(dockerConfigJson))}
type: kubernetes.io/dockerconfigjson`;
  }, [
    credentials.title,
    credentials.username,
    credentials.password,
    quayConfig?.config?.SERVER_HOSTNAME,
  ]);

  const rktConfig = useMemo(() => {
    const hostname = getServerHostname();
    return `{
  "rktKind": "auth",
  "rktVersion": "v1",
  "domains": ["${hostname}"],
  "type": "basic",
  "credentials": {
    "user": "${credentials.username}",
    "password": "${credentials.password}"
  }
}`;
  }, [
    credentials.username,
    credentials.password,
    quayConfig?.config?.SERVER_HOSTNAME,
  ]);

  const dockerConfig = useMemo(() => {
    const hostname = getServerHostname();
    return `{
  "auths": {
    "${hostname}": {
      "auth": "${btoa(`${credentials.username}:${credentials.password}`)}",
      "email": ""
    }
  }
}`;
  }, [
    credentials.username,
    credentials.password,
    quayConfig?.config?.SERVER_HOSTNAME,
  ]);

  const isToken = type === 'token';
  const firstTabTitle = isToken ? 'Application Token' : 'Encrypted Password';
  const passwordFieldLabel = isToken ? 'Token' : 'Encrypted Password';

  return (
    <Modal
      variant={ModalVariant.large}
      title={`Credentials for ${credentials.title}`}
      isOpen={isOpen}
      onClose={onClose}
      data-testid="credentials-modal"
      actions={[
        <Button
          key="done"
          variant="primary"
          onClick={onClose}
          data-testid="credentials-modal-close"
        >
          Done
        </Button>,
      ]}
    >
      {isNewlyCreated && isToken && (
        <Alert
          variant="success"
          isInline
          title="Token Created Successfully"
          className="pf-v5-u-mb-md"
        >
          Your application token has been created and can be used in place of
          your password for Docker and other CLI commands. Make sure to copy and
          save it securely.
        </Alert>
      )}
      {!isNewlyCreated && isToken && (
        <Alert
          variant="info"
          isInline
          title="Application Token"
          className="pf-v5-u-mb-md"
        >
          This token can be used in place of your password for Docker and other
          CLI commands. Keep it secure and do not share it.
        </Alert>
      )}
      {!isToken && (
        <Alert
          variant="info"
          isInline
          title="Encrypted Password"
          className="pf-v5-u-mb-md"
        >
          This encrypted password can be used for <code>docker login</code> and
          other CLI commands. It is recommended to use this instead of your
          plaintext password.
        </Alert>
      )}

      <Tabs
        activeKey={activeTabKey}
        onSelect={(_event, tabIndex) => setActiveTabKey(tabIndex)}
      >
        <Tab eventKey={0} title={<TabTitleText>{firstTabTitle}</TabTitleText>}>
          <Form className="pf-v5-u-p-md">
            <FormGroup
              label="Username"
              fieldId="username"
              className="pf-v5-u-mb-md"
            >
              <ClipboardCopy
                hoverTip="Copy"
                clickTip="Copied"
                isReadOnly
                data-testid="credentials-modal-copy-username"
              >
                {credentials.username}
              </ClipboardCopy>
            </FormGroup>
            <FormGroup label={passwordFieldLabel} fieldId="password">
              <ClipboardCopy
                hoverTip="Copy"
                clickTip="Copied"
                variant="expansion"
                isReadOnly
                data-testid="credentials-modal-copy-password"
              >
                {credentials.password}
              </ClipboardCopy>
            </FormGroup>
          </Form>
        </Tab>

        <Tab
          eventKey={1}
          title={<TabTitleText>Kubernetes Secret</TabTitleText>}
        >
          <div className="pf-v5-u-p-md">
            <FormGroup
              label="Step 1: Create secret YAML file"
              className="pf-v5-u-mb-md"
            >
              <CodeBlock>
                <CodeBlockCode>{kubernetesYaml}</CodeBlockCode>
              </CodeBlock>
            </FormGroup>
            <FormGroup
              label="Step 2: Apply the secret"
              className="pf-v5-u-mb-md"
            >
              <ClipboardCopy hoverTip="Copy" clickTip="Copied" isReadOnly>
                {`kubectl create -f ${credentials.title}-pull-secret.yaml --namespace=NAMESPACE`}
              </ClipboardCopy>
            </FormGroup>
            <FormGroup label="Step 3: Reference in pod spec">
              <Text component="small" className="pf-v5-u-mb-sm">
                Add the following to your pod configuration:
              </Text>
              <CodeBlock>
                <CodeBlockCode>
                  {`imagePullSecrets:\n  - name: ${credentials.title}-pull-secret`}
                </CodeBlockCode>
              </CodeBlock>
            </FormGroup>
          </div>
        </Tab>

        <Tab
          eventKey={2}
          title={<TabTitleText>rkt Configuration</TabTitleText>}
        >
          <div className="pf-v5-u-p-md">
            <FormGroup
              label="Step 1: Create rkt configuration file"
              className="pf-v5-u-mb-md"
            >
              <CodeBlock>
                <CodeBlockCode>{rktConfig}</CodeBlockCode>
              </CodeBlock>
            </FormGroup>
            <FormGroup label="Step 2: Place file in rkt auth directory">
              <ClipboardCopy hoverTip="Copy" clickTip="Copied" isReadOnly>
                {`mv ${getServerHostname()}.json /etc/rkt/auth.d/`}
              </ClipboardCopy>
            </FormGroup>
          </div>
        </Tab>

        <Tab eventKey={3} title={<TabTitleText>Podman Login</TabTitleText>}>
          <div className="pf-v5-u-p-md">
            <FormGroup label="Run podman login command">
              <ClipboardCopy hoverTip="Copy" clickTip="Copied" isReadOnly>
                {getContainerLoginCommand('podman')}
              </ClipboardCopy>
            </FormGroup>
          </div>
        </Tab>

        <Tab eventKey={4} title={<TabTitleText>Docker Login</TabTitleText>}>
          <div className="pf-v5-u-p-md">
            <FormGroup label="Run docker login command">
              <ClipboardCopy hoverTip="Copy" clickTip="Copied" isReadOnly>
                {getContainerLoginCommand('docker')}
              </ClipboardCopy>
            </FormGroup>
          </div>
        </Tab>

        <Tab
          eventKey={5}
          title={<TabTitleText>Docker Configuration</TabTitleText>}
        >
          <div className="pf-v5-u-p-md">
            <FormGroup
              label="Step 1: Create Docker config file"
              className="pf-v5-u-mb-md"
            >
              <CodeBlock>
                <CodeBlockCode>{dockerConfig}</CodeBlockCode>
              </CodeBlock>
            </FormGroup>
            <FormGroup label="Step 2: Place file in Docker directory">
              <Alert
                variant="warning"
                isInline
                title="Warning"
                className="pf-v5-u-mb-sm"
              >
                This will <strong>overwrite</strong> existing credentials
              </Alert>
              <ClipboardCopy hoverTip="Copy" clickTip="Copied" isReadOnly>
                mv config.json ~/.docker/config.json
              </ClipboardCopy>
            </FormGroup>
          </div>
        </Tab>
      </Tabs>
    </Modal>
  );
}
