import React, {useState} from 'react';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {
  Alert,
  Button,
  Checkbox,
  ClipboardCopy,
  Content,
  Form,
  FormGroup,
  FormSelect,
  FormSelectOption,
  Modal,
  ModalBody,
  ModalFooter,
  ModalHeader,
  ModalVariant,
  Spinner,
  Stack,
  StackItem,
  TextInput,
} from '@patternfly/react-core';
import {TrashIcon} from '@patternfly/react-icons';
import {
  createRobotAPIToken,
  fetchRobotAPITokens,
  revokeRobotAPIToken,
} from 'src/resources/RobotsResource';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {OAUTH_SCOPES} from 'src/routes/OrganizationsList/Organization/Tabs/OAuthApplications/types';

const DAY = 24 * 60 * 60;
const EXPIRATIONS = [
  {label: '7 days', seconds: 7 * DAY},
  {label: '30 days', seconds: 30 * DAY},
  {label: '90 days', seconds: 90 * DAY},
];

interface RobotAPITokensTabProps {
  namespace: string;
  robotName: string;
  isUserOrganization: boolean;
}

const RobotAPITokensTab: React.FC<RobotAPITokensTabProps> = ({
  namespace,
  robotName,
  isUserOrganization,
}): React.ReactElement => {
  const queryClient = useQueryClient();
  const quayConfig = useQuayConfig();
  const [isCreateOpen, setCreateOpen] = useState(false);
  const [generatedToken, setGeneratedToken] = useState<string | null>(null);
  const [name, setName] = useState('');
  const [selectedScopes, setSelectedScopes] = useState<string[]>([]);
  const [expiration, setExpiration] = useState(String(30 * DAY));
  const queryKey = [
    'robot-api-tokens',
    namespace,
    robotName,
    isUserOrganization,
  ];
  const shortName = robotName.split('+').pop() || robotName;

  const {
    data: tokens = [],
    isLoading,
    isError,
  } = useQuery(queryKey, () =>
    fetchRobotAPITokens(namespace, shortName, isUserOrganization),
  );
  const createMutation = useMutation(
    () =>
      createRobotAPIToken(
        namespace,
        shortName,
        {
          name: name.trim(),
          scope: selectedScopes.join(' '),
          expiration: Number(expiration),
        },
        isUserOrganization,
      ),
    {
      onSuccess: (token) => {
        queryClient.invalidateQueries(queryKey);
        setGeneratedToken(token.token || null);
        setCreateOpen(false);
        setName('');
        setSelectedScopes([]);
        setExpiration(String(30 * DAY));
      },
    },
  );
  const revokeMutation = useMutation(
    (tokenUuid: string) =>
      revokeRobotAPIToken(namespace, shortName, tokenUuid, isUserOrganization),
    {onSuccess: () => queryClient.invalidateQueries(queryKey)},
  );

  const toggleScope = (scope: string, checked: boolean): void => {
    setSelectedScopes((current) =>
      checked
        ? [...current, scope]
        : current.filter((selected) => selected !== scope),
    );
  };
  const canCreate =
    name.trim().length > 0 &&
    selectedScopes.length > 0 &&
    !createMutation.isLoading;

  return (
    <>
      <Stack hasGutter>
        <StackItem>
          <Content component="p">
            Create short-lived bearer tokens for Quay Management API access. The
            token acts as this robot and is shown only once.
          </Content>
        </StackItem>
        <StackItem>
          <Button variant="primary" onClick={() => setCreateOpen(true)}>
            Create API token
          </Button>
        </StackItem>
        {isLoading && <Spinner />}
        {isError && (
          <Alert
            variant="danger"
            isInline
            title="Unable to load robot API tokens"
          />
        )}
        {!isLoading && !isError && tokens.length === 0 && (
          <Content component="p">
            No API tokens have been created for this robot.
          </Content>
        )}
        {tokens.map((token) => (
          <StackItem key={token.uuid}>
            <Content component="p">
              <strong>{token.name || token.uuid}</strong> — {token.scope} —
              expires {token.expires_at}
              {token.created_by && ` — created by ${token.created_by}`}
            </Content>
            <Button
              variant="link"
              icon={<TrashIcon />}
              isDanger
              onClick={() => revokeMutation.mutate(token.uuid)}
              isLoading={revokeMutation.isLoading}
            >
              Revoke
            </Button>
          </StackItem>
        ))}
      </Stack>
      <Modal
        variant={ModalVariant.medium}
        isOpen={isCreateOpen}
        onClose={() => setCreateOpen(false)}
      >
        <ModalHeader title="Create robot API token" />
        <ModalBody>
          <Form>
            {createMutation.isError && (
              <Alert
                variant="danger"
                isInline
                title="Unable to create API token"
              />
            )}
            <FormGroup
              label="Token name"
              fieldId="robot-api-token-name"
              isRequired
            >
              <TextInput
                id="robot-api-token-name"
                value={name}
                onChange={(_event, value) => setName(value)}
              />
            </FormGroup>
            <FormGroup
              label="Expiration"
              fieldId="robot-api-token-expiration"
              isRequired
            >
              <FormSelect
                id="robot-api-token-expiration"
                value={expiration}
                onChange={(_event, value) => setExpiration(value)}
              >
                {EXPIRATIONS.map((option) => (
                  <FormSelectOption
                    key={option.seconds}
                    value={option.seconds}
                    label={option.label}
                  />
                ))}
              </FormSelect>
            </FormGroup>
            <FormGroup
              label="Scopes"
              fieldId="robot-api-token-scopes"
              isRequired
            >
              <Stack hasGutter>
                {Object.entries(OAUTH_SCOPES)
                  .filter(
                    ([scope]) =>
                      scope !== 'super:user' ||
                      quayConfig?.features?.SUPER_USERS === true,
                  )
                  .map(([scope, details]) => (
                    <StackItem key={scope}>
                      <Checkbox
                        id={`robot-api-token-scope-${scope}`}
                        label={details.title}
                        description={details.description}
                        isChecked={selectedScopes.includes(scope)}
                        onChange={(_event, checked) =>
                          toggleScope(scope, checked)
                        }
                      />
                    </StackItem>
                  ))}
              </Stack>
            </FormGroup>
          </Form>
        </ModalBody>
        <ModalFooter>
          <Button
            variant="primary"
            isDisabled={!canCreate}
            isLoading={createMutation.isLoading}
            onClick={() => createMutation.mutate()}
          >
            Create
          </Button>
          <Button variant="link" onClick={() => setCreateOpen(false)}>
            Cancel
          </Button>
        </ModalFooter>
      </Modal>
      <Modal
        variant={ModalVariant.medium}
        isOpen={generatedToken !== null}
        onClose={() => setGeneratedToken(null)}
      >
        <ModalHeader title="Robot API token created" />
        <ModalBody>
          <Alert
            variant="warning"
            isInline
            title="This is the only time this token secret will be displayed."
          />
          <ClipboardCopy
            isReadOnly
            isExpanded
            isCode
            variant="expansion"
            style={{overflowWrap: 'anywhere', whiteSpace: 'pre-wrap'}}
          >
            {generatedToken}
          </ClipboardCopy>
        </ModalBody>
        <ModalFooter>
          <Button variant="primary" onClick={() => setGeneratedToken(null)}>
            Done
          </Button>
        </ModalFooter>
      </Modal>
    </>
  );
};

export default RobotAPITokensTab;
