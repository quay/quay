import React, {useLayoutEffect, useMemo, useRef, useState} from 'react';
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
  Label,
  Modal,
  ModalBody,
  ModalFooter,
  ModalHeader,
  ModalVariant,
  Spinner,
  Stack,
  StackItem,
  TextInput,
  Toolbar,
  ToolbarContent,
  ToolbarItem,
  Tooltip,
} from '@patternfly/react-core';
import {Table, Tbody, Td, Th, Thead, Tr} from '@patternfly/react-table';
import {TrashIcon} from '@patternfly/react-icons';
import {BulkDeleteModalTemplate} from 'src/components/modals/BulkDeleteModalTemplate';
import {DropdownCheckbox} from 'src/components/toolbar/DropdownCheckbox';
import {SearchInput} from 'src/components/toolbar/SearchInput';
import {SearchState} from 'src/components/toolbar/SearchTypes';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';
import {formatDate, formatRelativeTime} from 'src/libs/utils';
import {
  createRobotAPIToken,
  fetchRobotAPITokens,
  fetchRobotMintableScopes,
  IRobotAPIToken,
  revokeRobotAPIToken,
} from 'src/resources/RobotsResource';
import {OAUTH_SCOPES} from 'src/routes/OrganizationsList/Organization/Tabs/OAuthApplications/types';

const DAY = 24 * 60 * 60;
const EXPIRATIONS = [
  {label: '7 days', seconds: 7 * DAY},
  {label: '30 days', seconds: 30 * DAY},
  {label: '90 days', seconds: 90 * DAY},
];

const DEFAULT_PER_PAGE = 10;

const tokenDisplayName = (token: IRobotAPIToken): string =>
  token.name || token.uuid;

const RelativeDate: React.FC<{value: string | null}> = ({
  value,
}): React.ReactElement => {
  if (!value) {
    return <>Never</>;
  }
  return (
    <Tooltip content={formatDate(value)}>
      <span>{formatRelativeTime(value)}</span>
    </Tooltip>
  );
};

const ExpiryDate: React.FC<{value: string}> = ({value}): React.ReactElement => {
  const isExpired = Date.parse(value) <= Date.now();
  return (
    <Tooltip content={formatDate(value)}>
      <span>
        {formatRelativeTime(value)}
        {isExpired && (
          <>
            {' '}
            <Label color="red" isCompact>
              Expired
            </Label>
          </>
        )}
      </span>
    </Tooltip>
  );
};

interface BulkRevokeFailure {
  failedNames: string[];
  total: number;
}

interface RobotAPITokensTabProps {
  namespace: string;
  robotName: string;
  isUserOrganization: boolean;
  canManageRobotAPITokens: boolean;
}

const RobotAPITokensTab: React.FC<RobotAPITokensTabProps> = ({
  namespace,
  robotName,
  isUserOrganization,
  canManageRobotAPITokens,
}): React.ReactElement => {
  const queryClient = useQueryClient();
  const canManageRobotAPITokensRef = useRef(canManageRobotAPITokens);
  const permissionGenerationRef = useRef(0);
  const createPermissionGenerationRef = useRef<number | null>(null);
  const [isCreateOpen, setCreateOpen] = useState(false);
  const [generatedToken, setGeneratedToken] = useState<string | null>(null);
  const [name, setName] = useState('');
  const [selectedScopes, setSelectedScopes] = useState<string[]>([]);
  const [expiration, setExpiration] = useState(String(30 * DAY));
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(DEFAULT_PER_PAGE);
  const [search, setSearch] = useState<SearchState>({
    query: '',
    field: 'name',
  });
  const [selectedTokens, setSelectedTokens] = useState<IRobotAPIToken[]>([]);
  const [isBulkRevokeOpen, setBulkRevokeOpen] = useState(false);
  const [bulkRevokeFailure, setBulkRevokeFailure] =
    useState<BulkRevokeFailure | null>(null);
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
  const {
    data: mintableScopes = [],
    isLoading: isLoadingMintableScopes,
    isError: isMintableScopesError,
  } = useQuery(
    ['robot-mintable-scopes', namespace, robotName, isUserOrganization],
    () => fetchRobotMintableScopes(namespace, robotName, isUserOrganization),
    {enabled: isCreateOpen},
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
        const canDisplayGeneratedToken =
          canManageRobotAPITokensRef.current &&
          createPermissionGenerationRef.current ===
            permissionGenerationRef.current;
        createPermissionGenerationRef.current = null;
        if (canDisplayGeneratedToken) {
          setGeneratedToken(token.token || null);
        }
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

  const filteredTokens = useMemo(() => {
    const query = search.query.trim().toLowerCase();
    return query
      ? tokens.filter((token) =>
          tokenDisplayName(token).toLowerCase().includes(query),
        )
      : tokens;
  }, [tokens, search.query]);
  const lastPage = Math.max(1, Math.ceil(filteredTokens.length / perPage));
  const currentPage = Math.min(page, lastPage);
  const paginatedTokens = filteredTokens.slice(
    (currentPage - 1) * perPage,
    currentPage * perPage,
  );
  const isTokenSelected = (token: IRobotAPIToken): boolean =>
    selectedTokens.some((selected) => selected.uuid === token.uuid);
  const tokensForBulkRevoke = tokens.filter(isTokenSelected);

  useLayoutEffect(() => {
    if (canManageRobotAPITokensRef.current !== canManageRobotAPITokens) {
      canManageRobotAPITokensRef.current = canManageRobotAPITokens;
      permissionGenerationRef.current += 1;
    }
    if (!canManageRobotAPITokens) {
      setCreateOpen(false);
      setBulkRevokeOpen(false);
      setSelectedTokens([]);
      setBulkRevokeFailure(null);
      setGeneratedToken(null);
      createPermissionGenerationRef.current = null;
    }
  }, [canManageRobotAPITokens]);

  const onSearchChange = (
    value: SearchState | ((current: SearchState) => SearchState),
  ): void => {
    setSearch(value);
    setPage(1);
  };
  const onSelectToken = (
    token: IRobotAPIToken,
    _rowIndex: number,
    isSelecting: boolean,
  ): void => {
    setSelectedTokens((current) => {
      const others = current.filter((selected) => selected.uuid !== token.uuid);
      return isSelecting ? [...others, token] : others;
    });
  };
  const bulkRevoke = async (items: IRobotAPIToken[]): Promise<void> => {
    if (!canManageRobotAPITokens) {
      return;
    }
    const bulkRevokePermissionGeneration = permissionGenerationRef.current;
    const results = await Promise.allSettled(
      items.map((token) =>
        revokeRobotAPIToken(
          namespace,
          shortName,
          token.uuid,
          isUserOrganization,
        ),
      ),
    );
    const failed = items.filter(
      (_token, index) => results[index].status === 'rejected',
    );
    if (
      canManageRobotAPITokensRef.current &&
      permissionGenerationRef.current === bulkRevokePermissionGeneration
    ) {
      setBulkRevokeFailure(
        failed.length > 0
          ? {failedNames: failed.map(tokenDisplayName), total: items.length}
          : null,
      );
      setSelectedTokens(failed);
      setBulkRevokeOpen(false);
    }
    queryClient.invalidateQueries(queryKey);
  };

  const clearCreateError = (): void => {
    if (!createMutation.isLoading) {
      createMutation.reset();
    }
  };
  const openCreate = (): void => {
    if (canManageRobotAPITokens) {
      clearCreateError();
      setCreateOpen(true);
    }
  };
  const toggleScope = (scope: string, checked: boolean): void => {
    clearCreateError();
    setSelectedScopes((current) =>
      checked
        ? [...current, scope]
        : current.filter((selected) => selected !== scope),
    );
  };
  const canCreate =
    canManageRobotAPITokens &&
    name.trim().length > 0 &&
    selectedScopes.length > 0 &&
    !isLoadingMintableScopes &&
    !isMintableScopesError &&
    !createMutation.isLoading;
  const submitCreate = (event?: React.FormEvent<HTMLFormElement>): void => {
    event?.preventDefault();
    if (canManageRobotAPITokens && canCreate) {
      createPermissionGenerationRef.current = permissionGenerationRef.current;
      createMutation.mutate();
    }
  };

  return (
    <>
      <Stack hasGutter>
        <StackItem>
          <Content component="p">
            Create short-lived bearer tokens for Quay Management API access. The
            token acts as this robot and is shown only once.
          </Content>
        </StackItem>
        {canManageRobotAPITokens && (
          <StackItem>
            <Button variant="primary" onClick={openCreate}>
              Create API token
            </Button>
          </StackItem>
        )}
        {isLoading && <Spinner />}
        {isError && (
          <Alert
            variant="danger"
            isInline
            title="Unable to load robot API tokens"
          />
        )}
        {revokeMutation.isError && (
          <Alert
            variant="danger"
            isInline
            title="Unable to revoke robot API token; it remains active"
          />
        )}
        {bulkRevokeFailure && (
          <Alert
            variant="danger"
            isInline
            title={`Unable to revoke ${bulkRevokeFailure.failedNames.length} of ${bulkRevokeFailure.total} selected tokens; they remain active: ${bulkRevokeFailure.failedNames.join(', ')}`}
          />
        )}
        {!isLoading && !isError && tokens.length === 0 && (
          <Content component="p">
            No API tokens have been created for this robot.
          </Content>
        )}
        {tokens.length > 0 && (
          <StackItem>
            <Toolbar
              id="robot-api-tokens-toolbar"
              inset={{default: 'insetNone'}}
            >
              <ToolbarContent>
                {canManageRobotAPITokens && (
                  <DropdownCheckbox
                    selectedItems={selectedTokens}
                    deSelectAll={setSelectedTokens}
                    allItemsList={filteredTokens}
                    itemsPerPageList={paginatedTokens}
                    onItemSelect={onSelectToken}
                    id="robot-api-token-dropdown-checkbox"
                  />
                )}
                <SearchInput
                  id="robot-api-token-search"
                  searchState={search}
                  onChange={onSearchChange}
                  allowSpaces={true}
                />
                {canManageRobotAPITokens && selectedTokens.length > 0 && (
                  <ToolbarItem>
                    <Button
                      variant="danger"
                      onClick={() => setBulkRevokeOpen(true)}
                    >
                      Revoke selected
                    </Button>
                  </ToolbarItem>
                )}
                <ToolbarPagination
                  id="robot-api-tokens-pagination"
                  itemsList={filteredTokens}
                  perPage={perPage}
                  page={currentPage}
                  setPage={setPage}
                  setPerPage={setPerPage}
                  isCompact={true}
                />
              </ToolbarContent>
            </Toolbar>
            {filteredTokens.length === 0 ? (
              <Content component="p">No API tokens match the search.</Content>
            ) : (
              <Table
                aria-label="Robot API tokens table"
                data-testid="robot-api-tokens-table"
                variant="compact"
              >
                <Thead>
                  <Tr>
                    {canManageRobotAPITokens && (
                      <Th screenReaderText="Row select" />
                    )}
                    <Th width={30}>Token name</Th>
                    <Th width={20}>Scopes</Th>
                    <Th width={15}>Expires</Th>
                    <Th width={15}>Last accessed</Th>
                    <Th width={10}>Created by</Th>
                    {canManageRobotAPITokens && (
                      <Th screenReaderText="Actions" />
                    )}
                  </Tr>
                </Thead>
                <Tbody>
                  {paginatedTokens.map((token, rowIndex) => (
                    <Tr key={token.uuid}>
                      {canManageRobotAPITokens && (
                        <Td
                          select={{
                            rowIndex,
                            onSelect: (_event, isSelecting) =>
                              onSelectToken(token, rowIndex, isSelecting),
                            isSelected: isTokenSelected(token),
                          }}
                        />
                      )}
                      <Td dataLabel="Token name" modifier="truncate">
                        <Tooltip content={tokenDisplayName(token)}>
                          <span
                            style={{
                              display: 'block',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                            }}
                          >
                            {tokenDisplayName(token)}
                          </span>
                        </Tooltip>
                      </Td>
                      <Td dataLabel="Scopes" modifier="breakWord">
                        {token.scope}
                      </Td>
                      <Td dataLabel="Expires" modifier="nowrap">
                        <ExpiryDate value={token.expires_at} />
                      </Td>
                      <Td dataLabel="Last accessed" modifier="nowrap">
                        <RelativeDate value={token.last_accessed} />
                      </Td>
                      <Td dataLabel="Created by">{token.created_by}</Td>
                      {canManageRobotAPITokens && (
                        <Td isActionCell>
                          <Button
                            variant="link"
                            icon={<TrashIcon />}
                            isDanger
                            onClick={() => revokeMutation.mutate(token.uuid)}
                            isLoading={
                              revokeMutation.isLoading &&
                              revokeMutation.variables === token.uuid
                            }
                            isDisabled={revokeMutation.isLoading}
                          >
                            Revoke
                          </Button>
                        </Td>
                      )}
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            )}
          </StackItem>
        )}
      </Stack>
      {canManageRobotAPITokens && isBulkRevokeOpen && (
        <BulkDeleteModalTemplate
          mapOfColNamesToTableData={{
            'Token name': {label: 'name', transformFunc: tokenDisplayName},
            Scopes: {label: 'scope'},
            Expires: {
              label: 'expires_at',
              transformFunc: (token: IRobotAPIToken) =>
                formatRelativeTime(token.expires_at),
            },
          }}
          handleModalToggle={() => setBulkRevokeOpen(false)}
          handleBulkDeletion={bulkRevoke}
          isModalOpen={isBulkRevokeOpen}
          selectedItems={tokensForBulkRevoke}
          resourceName="robot API tokens"
          title={`Revoke ${tokensForBulkRevoke.length} robot API token${
            tokensForBulkRevoke.length === 1 ? '' : 's'
          }?`}
          description="Only the selected tokens are revoked. A revoked token stops working at once and cannot be restored."
          confirmationLabel="Confirm revocation by typing"
          actionLabel="Revoke"
        />
      )}
      {canManageRobotAPITokens && (
        <Modal
          variant={ModalVariant.medium}
          isOpen={isCreateOpen}
          onClose={() => setCreateOpen(false)}
        >
          <ModalHeader title="Create robot API token" />
          <ModalBody>
            <Form id="create-robot-api-token-form" onSubmit={submitCreate}>
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
                  onChange={(_event, value) => {
                    clearCreateError();
                    setName(value);
                  }}
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
                  onChange={(_event, value) => {
                    clearCreateError();
                    setExpiration(value);
                  }}
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
                {isLoadingMintableScopes && <Spinner />}
                {isMintableScopesError && (
                  <Alert
                    variant="danger"
                    isInline
                    title="Unable to load scopes you can grant"
                  />
                )}
                {!isLoadingMintableScopes && !isMintableScopesError && (
                  <Stack hasGutter>
                    {Object.entries(OAUTH_SCOPES)
                      .filter(([scope]) => mintableScopes.includes(scope))
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
                )}
              </FormGroup>
            </Form>
          </ModalBody>
          <ModalFooter>
            <Button
              variant="primary"
              type="submit"
              form="create-robot-api-token-form"
              isDisabled={!canCreate}
              isLoading={createMutation.isLoading}
            >
              Create
            </Button>
            <Button variant="link" onClick={() => setCreateOpen(false)}>
              Cancel
            </Button>
          </ModalFooter>
        </Modal>
      )}
      <Modal
        variant={ModalVariant.medium}
        isOpen={canManageRobotAPITokens && generatedToken !== null}
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
