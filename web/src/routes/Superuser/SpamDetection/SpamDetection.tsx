import {
  PageSection,
  Title,
  Tabs,
  Tab,
  TabTitleText,
  Spinner,
  Alert,
  Button,
  Label,
  Modal,
  ModalBody,
  ModalFooter,
  ModalHeader,
  ModalVariant,
  Toolbar,
  ToolbarContent,
  ToolbarItem,
  Dropdown,
  DropdownList,
  DropdownItem,
  MenuToggle,
  TextInput,
  FormGroup,
  Form,
  FormSelect,
  FormSelectOption,
  Split,
  SplitItem,
  DescriptionList,
  DescriptionListGroup,
  DescriptionListTerm,
  DescriptionListDescription,
  Switch,
} from '@patternfly/react-core';
import {
  ShieldAltIcon,
  PlusIcon,
  TrashIcon,
  CogIcon,
  EditAltIcon,
  CheckCircleIcon,
  BanIcon,
  UndoIcon,
  SearchIcon,
} from '@patternfly/react-icons';
import {Table, Thead, Tr, Th, Tbody, Td} from '@patternfly/react-table';
import {useState} from 'react';
import {Navigate} from 'react-router-dom';
import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import {QuayBreadcrumb} from 'src/components/breadcrumb/Breadcrumb';
import Empty from 'src/components/empty/Empty';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
import {useSuperuserPermissions} from 'src/hooks/UseSuperuserPermissions';
import {
  fetchSpamRules,
  createSpamRule,
  updateSpamRule,
  deleteSpamRule,
  fetchFlaggedRepos,
  quarantineRepo,
  restoreRepo,
  dismissRepo,
  triggerSpamScan,
  ISpamDetectionRule,
  IFlaggedRepo,
  CreateSpamRuleRequest,
} from 'src/resources/SpamDetectionResource';

const RULE_TYPES = [
  {value: 'keyword', label: 'Keyword Match'},
  {value: 'url_pattern', label: 'URL Pattern (Regex)'},
  {value: 'repo_name_pattern', label: 'Repository Name Pattern (Regex)'},
  {value: 'empty_repo', label: 'Empty Repository'},
  {value: 'account_age', label: 'Account Age'},
];

function StatusLabel({status}: {status: string}) {
  const config: Record<
    string,
    {color: 'blue' | 'orange' | 'green' | 'grey'; icon: React.ReactNode}
  > = {
    flagged: {color: 'orange', icon: <ShieldAltIcon />},
    quarantined: {color: 'blue', icon: <BanIcon />},
    restored: {color: 'green', icon: <UndoIcon />},
    dismissed: {color: 'grey', icon: <CheckCircleIcon />},
  };
  const c = config[status] || {color: 'grey' as const, icon: null};
  return (
    <Label color={c.color} icon={c.icon}>
      {status}
    </Label>
  );
}

function SpamDetectionHeader() {
  return (
    <>
      <QuayBreadcrumb />
      <PageSection hasBodyWrapper={false} hasShadowBottom>
        <Title headingLevel="h1">Spam Detection</Title>
      </PageSection>
    </>
  );
}

function RulesTab() {
  const queryClient = useQueryClient();
  const {canModify} = useSuperuserPermissions();
  const {
    data: rules = [],
    isLoading,
    error,
  } = useQuery({
    queryKey: ['spam-rules'],
    queryFn: fetchSpamRules,
  });

  const createMutation = useMutation({
    mutationFn: (data: CreateSpamRuleRequest) => createSpamRule(data),
    onSuccess: () => queryClient.invalidateQueries({queryKey: ['spam-rules']}),
  });
  const deleteMutation = useMutation({
    mutationFn: (uuid: string) => deleteSpamRule(uuid),
    onSuccess: () => queryClient.invalidateQueries({queryKey: ['spam-rules']}),
  });
  const updateMutation = useMutation({
    mutationFn: ({
      uuid,
      data,
    }: {
      uuid: string;
      data: Partial<CreateSpamRuleRequest>;
    }) => updateSpamRule(uuid, data),
    onSuccess: () => queryClient.invalidateQueries({queryKey: ['spam-rules']}),
  });

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [ruleToDelete, setRuleToDelete] = useState<ISpamDetectionRule | null>(
    null,
  );
  const [openMenus, setOpenMenus] = useState<Record<string, boolean>>({});
  const [newRule, setNewRule] = useState<CreateSpamRuleRequest>({
    name: '',
    rule_type: 'keyword',
    pattern: '',
    confidence_score: 50,
    enabled: true,
  });

  const handleCreate = async () => {
    try {
      await createMutation.mutateAsync(newRule);
      setIsCreateOpen(false);
      setNewRule({
        name: '',
        rule_type: 'keyword',
        pattern: '',
        confidence_score: 50,
        enabled: true,
      });
    } catch (e) {
      // Error shown via mutation state
    }
  };

  const confirmDelete = async () => {
    if (!ruleToDelete) return;
    try {
      await deleteMutation.mutateAsync(ruleToDelete.uuid);
      setIsDeleteOpen(false);
      setRuleToDelete(null);
    } catch (e) {
      setIsDeleteOpen(false);
    }
  };

  const toggleEnabled = async (rule: ISpamDetectionRule) => {
    await updateMutation.mutateAsync({
      uuid: rule.uuid,
      data: {enabled: !rule.enabled},
    });
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
      <Alert variant="danger" title="Error loading rules">
        Failed to load spam detection rules.
      </Alert>
    );
  }

  return (
    <>
      <Toolbar>
        <ToolbarContent>
          <ToolbarItem>
            <Button
              variant="primary"
              icon={<PlusIcon />}
              onClick={() => setIsCreateOpen(true)}
              isDisabled={!canModify}
            >
              Create Rule
            </Button>
          </ToolbarItem>
        </ToolbarContent>
      </Toolbar>

      {rules.length === 0 ? (
        <Empty
          title="No Rules"
          icon={ShieldAltIcon}
          body="No spam detection rules configured. Create a rule to start scanning."
        />
      ) : (
        <Table aria-label="Spam Detection Rules" variant="compact">
          <Thead>
            <Tr>
              <Th>Name</Th>
              <Th>Type</Th>
              <Th>Pattern</Th>
              <Th>Confidence</Th>
              <Th>Enabled</Th>
              <Th></Th>
            </Tr>
          </Thead>
          <Tbody>
            {rules.map((rule) => (
              <Tr key={rule.uuid}>
                <Td>{rule.name}</Td>
                <Td>
                  {RULE_TYPES.find((t) => t.value === rule.rule_type)?.label ||
                    rule.rule_type}
                </Td>
                <Td>{rule.pattern || '-'}</Td>
                <Td>{rule.confidence_score}</Td>
                <Td>
                  <Switch
                    isChecked={rule.enabled}
                    onChange={() => toggleEnabled(rule)}
                    isDisabled={!canModify}
                    aria-label={`Toggle ${rule.name}`}
                  />
                </Td>
                <Td>
                  <Dropdown
                    toggle={(toggleRef) => (
                      <MenuToggle
                        ref={toggleRef}
                        variant="plain"
                        onClick={() =>
                          setOpenMenus((p) => ({
                            ...p,
                            [rule.uuid]: !p[rule.uuid],
                          }))
                        }
                        isExpanded={openMenus[rule.uuid]}
                      >
                        <CogIcon />
                      </MenuToggle>
                    )}
                    isOpen={openMenus[rule.uuid] || false}
                    onOpenChange={(isOpen) =>
                      setOpenMenus((p) => ({...p, [rule.uuid]: isOpen}))
                    }
                    popperProps={{position: 'right'}}
                  >
                    <DropdownList>
                      <DropdownItem
                        key="delete"
                        icon={<TrashIcon />}
                        isAriaDisabled={!canModify}
                        onClick={() => {
                          setRuleToDelete(rule);
                          setIsDeleteOpen(true);
                          setOpenMenus({});
                        }}
                      >
                        Delete Rule
                      </DropdownItem>
                    </DropdownList>
                  </Dropdown>
                </Td>
              </Tr>
            ))}
          </Tbody>
        </Table>
      )}

      <Modal
        variant={ModalVariant.medium}
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
      >
        <ModalHeader title="Create Detection Rule" />
        <ModalBody>
          <Form>
            <FormGroup label="Name" isRequired fieldId="rule-name">
              <TextInput
                id="rule-name"
                value={newRule.name}
                onChange={(_e, val) => setNewRule({...newRule, name: val})}
                isRequired
              />
            </FormGroup>
            <FormGroup label="Rule Type" isRequired fieldId="rule-type">
              <FormSelect
                id="rule-type"
                value={newRule.rule_type}
                onChange={(_e, val) => setNewRule({...newRule, rule_type: val})}
              >
                {RULE_TYPES.map((t) => (
                  <FormSelectOption
                    key={t.value}
                    value={t.value}
                    label={t.label}
                  />
                ))}
              </FormSelect>
            </FormGroup>
            {newRule.rule_type !== 'empty_repo' &&
              newRule.rule_type !== 'account_age' && (
                <FormGroup
                  label="Pattern"
                  fieldId="rule-pattern"
                  helperText={
                    newRule.rule_type === 'keyword'
                      ? 'Comma-separated keywords'
                      : 'Regular expression'
                  }
                >
                  <TextInput
                    id="rule-pattern"
                    value={newRule.pattern || ''}
                    onChange={(_e, val) =>
                      setNewRule({...newRule, pattern: val})
                    }
                  />
                </FormGroup>
              )}
            <FormGroup
              label="Confidence Score (0-100)"
              fieldId="rule-confidence"
            >
              <TextInput
                id="rule-confidence"
                type="number"
                value={newRule.confidence_score}
                onChange={(_e, val) =>
                  setNewRule({...newRule, confidence_score: parseInt(val) || 0})
                }
                min={0}
                max={100}
              />
            </FormGroup>
          </Form>
          {createMutation.isError && (
            <Alert variant="danger" title="Error" isInline>
              {String(
                (createMutation.error as Error)?.message ||
                  'Failed to create rule',
              )}
            </Alert>
          )}
        </ModalBody>
        <ModalFooter>
          <Button
            variant="primary"
            onClick={handleCreate}
            isLoading={createMutation.isLoading}
            isDisabled={!newRule.name || createMutation.isLoading}
          >
            Create
          </Button>
          <Button variant="link" onClick={() => setIsCreateOpen(false)}>
            Cancel
          </Button>
        </ModalFooter>
      </Modal>

      <Modal
        variant={ModalVariant.small}
        isOpen={isDeleteOpen}
        onClose={() => setIsDeleteOpen(false)}
      >
        <ModalHeader title="Delete Rule?" />
        <ModalBody>
          Are you sure you want to delete rule &quot;{ruleToDelete?.name}&quot;?
        </ModalBody>
        <ModalFooter>
          <Button
            variant="danger"
            onClick={confirmDelete}
            isLoading={deleteMutation.isLoading}
          >
            Delete
          </Button>
          <Button variant="link" onClick={() => setIsDeleteOpen(false)}>
            Cancel
          </Button>
        </ModalFooter>
      </Modal>
    </>
  );
}

function FlaggedReposTab() {
  const queryClient = useQueryClient();
  const {canModify} = useSuperuserPermissions();
  const [statusFilter, setStatusFilter] = useState<string>('flagged');
  const {data, isLoading, error} = useQuery({
    queryKey: ['flagged-repos', statusFilter],
    queryFn: () =>
      fetchFlaggedRepos({status: statusFilter || undefined, limit: 50}),
  });

  const quarantineMutation = useMutation({
    mutationFn: quarantineRepo,
    onSuccess: () =>
      queryClient.invalidateQueries({queryKey: ['flagged-repos']}),
  });
  const restoreMutation = useMutation({
    mutationFn: restoreRepo,
    onSuccess: () =>
      queryClient.invalidateQueries({queryKey: ['flagged-repos']}),
  });
  const dismissMutation = useMutation({
    mutationFn: dismissRepo,
    onSuccess: () =>
      queryClient.invalidateQueries({queryKey: ['flagged-repos']}),
  });

  const [openMenus, setOpenMenus] = useState<Record<string, boolean>>({});
  const [selectedRepo, setSelectedRepo] = useState<IFlaggedRepo | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);

  const repos = data?.flagged_repos || [];

  if (isLoading) {
    return (
      <div style={{textAlign: 'center', padding: '2rem'}}>
        <Spinner size="lg" />
      </div>
    );
  }
  if (error) {
    return (
      <Alert variant="danger" title="Error loading flagged repos">
        Failed to load flagged repositories.
      </Alert>
    );
  }

  return (
    <>
      <Toolbar>
        <ToolbarContent>
          <ToolbarItem>
            <FormSelect
              value={statusFilter}
              onChange={(_e, val) => setStatusFilter(val)}
              aria-label="Filter by status"
              style={{width: '200px'}}
            >
              <FormSelectOption value="" label="All Statuses" />
              <FormSelectOption value="flagged" label="Flagged" />
              <FormSelectOption value="quarantined" label="Quarantined" />
              <FormSelectOption value="restored" label="Restored" />
              <FormSelectOption value="dismissed" label="Dismissed" />
            </FormSelect>
          </ToolbarItem>
        </ToolbarContent>
      </Toolbar>

      {repos.length === 0 ? (
        <Empty
          title="No Flagged Repositories"
          icon={SearchIcon}
          body="No repositories match the current filter."
        />
      ) : (
        <Table aria-label="Flagged Repositories" variant="compact">
          <Thead>
            <Tr>
              <Th>Repository</Th>
              <Th>Status</Th>
              <Th>Confidence</Th>
              <Th>Rules Matched</Th>
              <Th>Empty</Th>
              <Th>Flagged At</Th>
              <Th></Th>
            </Tr>
          </Thead>
          <Tbody>
            {repos.map((repo) => (
              <Tr key={repo.uuid}>
                <Td>
                  <Button
                    variant="link"
                    isInline
                    onClick={() => {
                      setSelectedRepo(repo);
                      setDetailOpen(true);
                    }}
                  >
                    {repo.namespace_name}/{repo.repository_name}
                  </Button>
                </Td>
                <Td>
                  <StatusLabel status={repo.status} />
                </Td>
                <Td>{repo.total_confidence_score}</Td>
                <Td>{repo.matched_rules?.length || 0}</Td>
                <Td>{repo.is_empty ? 'Yes' : 'No'}</Td>
                <Td>{repo.created_at || '-'}</Td>
                <Td>
                  <Dropdown
                    toggle={(toggleRef) => (
                      <MenuToggle
                        ref={toggleRef}
                        variant="plain"
                        onClick={() =>
                          setOpenMenus((p) => ({
                            ...p,
                            [repo.uuid]: !p[repo.uuid],
                          }))
                        }
                        isExpanded={openMenus[repo.uuid]}
                      >
                        <CogIcon />
                      </MenuToggle>
                    )}
                    isOpen={openMenus[repo.uuid] || false}
                    onOpenChange={(isOpen) =>
                      setOpenMenus((p) => ({...p, [repo.uuid]: isOpen}))
                    }
                    popperProps={{position: 'right'}}
                  >
                    <DropdownList>
                      {repo.status === 'flagged' && (
                        <>
                          <DropdownItem
                            key="quarantine"
                            icon={<BanIcon />}
                            isAriaDisabled={!canModify}
                            onClick={() => {
                              quarantineMutation.mutate(repo.uuid);
                              setOpenMenus({});
                            }}
                          >
                            Quarantine
                          </DropdownItem>
                          <DropdownItem
                            key="dismiss"
                            icon={<CheckCircleIcon />}
                            isAriaDisabled={!canModify}
                            onClick={() => {
                              dismissMutation.mutate(repo.uuid);
                              setOpenMenus({});
                            }}
                          >
                            Dismiss
                          </DropdownItem>
                        </>
                      )}
                      {repo.status === 'quarantined' && (
                        <DropdownItem
                          key="restore"
                          icon={<UndoIcon />}
                          isAriaDisabled={!canModify}
                          onClick={() => {
                            restoreMutation.mutate(repo.uuid);
                            setOpenMenus({});
                          }}
                        >
                          Restore
                        </DropdownItem>
                      )}
                    </DropdownList>
                  </Dropdown>
                </Td>
              </Tr>
            ))}
          </Tbody>
        </Table>
      )}

      <Modal
        variant={ModalVariant.large}
        isOpen={detailOpen}
        onClose={() => setDetailOpen(false)}
      >
        <ModalHeader
          title={
            selectedRepo
              ? `${selectedRepo.namespace_name}/${selectedRepo.repository_name}`
              : ''
          }
        />
        <ModalBody>
          {selectedRepo && (
            <DescriptionList>
              <DescriptionListGroup>
                <DescriptionListTerm>Status</DescriptionListTerm>
                <DescriptionListDescription>
                  <StatusLabel status={selectedRepo.status} />
                </DescriptionListDescription>
              </DescriptionListGroup>
              <DescriptionListGroup>
                <DescriptionListTerm>Confidence Score</DescriptionListTerm>
                <DescriptionListDescription>
                  {selectedRepo.total_confidence_score}
                </DescriptionListDescription>
              </DescriptionListGroup>
              <DescriptionListGroup>
                <DescriptionListTerm>Empty Repository</DescriptionListTerm>
                <DescriptionListDescription>
                  {selectedRepo.is_empty ? 'Yes' : 'No'}
                </DescriptionListDescription>
              </DescriptionListGroup>
              <DescriptionListGroup>
                <DescriptionListTerm>Original Description</DescriptionListTerm>
                <DescriptionListDescription>
                  {selectedRepo.original_description || '(none)'}
                </DescriptionListDescription>
              </DescriptionListGroup>
              <DescriptionListGroup>
                <DescriptionListTerm>Matched Rules</DescriptionListTerm>
                <DescriptionListDescription>
                  {selectedRepo.matched_rules?.map((r, i) => (
                    <div key={i}>
                      {r.rule_name} ({r.rule_type}) - confidence: {r.confidence}
                    </div>
                  ))}
                </DescriptionListDescription>
              </DescriptionListGroup>
              {selectedRepo.actioned_by && (
                <DescriptionListGroup>
                  <DescriptionListTerm>Actioned By</DescriptionListTerm>
                  <DescriptionListDescription>
                    {selectedRepo.actioned_by} at {selectedRepo.actioned_at}
                  </DescriptionListDescription>
                </DescriptionListGroup>
              )}
            </DescriptionList>
          )}
        </ModalBody>
        <ModalFooter>
          <Button variant="link" onClick={() => setDetailOpen(false)}>
            Close
          </Button>
        </ModalFooter>
      </Modal>
    </>
  );
}

function ScanTab() {
  const {canModify} = useSuperuserPermissions();
  const scanMutation = useMutation({mutationFn: triggerSpamScan});

  return (
    <div style={{padding: '1rem'}}>
      <Split hasGutter>
        <SplitItem>
          <Button
            variant="primary"
            icon={<SearchIcon />}
            onClick={() => scanMutation.mutate()}
            isLoading={scanMutation.isLoading}
            isDisabled={!canModify || scanMutation.isLoading}
          >
            Run Scan
          </Button>
        </SplitItem>
      </Split>

      {scanMutation.isError && (
        <Alert
          variant="danger"
          title="Scan Failed"
          isInline
          style={{marginTop: '1rem'}}
        >
          {String(
            (scanMutation.error as Error)?.message || 'Failed to run scan',
          )}
        </Alert>
      )}

      {scanMutation.data && (
        <div style={{marginTop: '1rem'}}>
          <Alert variant="success" title="Scan Complete" isInline>
            Scan ID: {scanMutation.data.scan_id}
          </Alert>
          <DescriptionList style={{marginTop: '1rem'}}>
            <DescriptionListGroup>
              <DescriptionListTerm>Total Scanned</DescriptionListTerm>
              <DescriptionListDescription>
                {scanMutation.data.total_scanned}
              </DescriptionListDescription>
            </DescriptionListGroup>
            <DescriptionListGroup>
              <DescriptionListTerm>Flagged</DescriptionListTerm>
              <DescriptionListDescription>
                {scanMutation.data.flagged}
              </DescriptionListDescription>
            </DescriptionListGroup>
            <DescriptionListGroup>
              <DescriptionListTerm>Clean</DescriptionListTerm>
              <DescriptionListDescription>
                {scanMutation.data.clean}
              </DescriptionListDescription>
            </DescriptionListGroup>
            <DescriptionListGroup>
              <DescriptionListTerm>Skipped</DescriptionListTerm>
              <DescriptionListDescription>
                {scanMutation.data.skipped}
              </DescriptionListDescription>
            </DescriptionListGroup>
            <DescriptionListGroup>
              <DescriptionListTerm>Below Threshold</DescriptionListTerm>
              <DescriptionListDescription>
                {scanMutation.data.below_threshold}
              </DescriptionListDescription>
            </DescriptionListGroup>
            <DescriptionListGroup>
              <DescriptionListTerm>Errors</DescriptionListTerm>
              <DescriptionListDescription>
                {scanMutation.data.errors}
              </DescriptionListDescription>
            </DescriptionListGroup>
          </DescriptionList>
        </div>
      )}
    </div>
  );
}

export default function SpamDetection() {
  const {isSuperUser, loading: userLoading} = useCurrentUser();
  const [activeTab, setActiveTab] = useState<string | number>(0);

  if (userLoading) {
    return null;
  }

  if (!isSuperUser) {
    return <Navigate to="/organization" replace />;
  }

  return (
    <>
      <SpamDetectionHeader />
      <PageSection hasBodyWrapper={false}>
        <Tabs
          activeKey={activeTab}
          onSelect={(_e, key) => setActiveTab(key)}
          aria-label="Spam Detection Tabs"
        >
          <Tab
            eventKey={0}
            title={<TabTitleText>Flagged Repositories</TabTitleText>}
          >
            <FlaggedReposTab />
          </Tab>
          <Tab eventKey={1} title={<TabTitleText>Rules</TabTitleText>}>
            <RulesTab />
          </Tab>
          <Tab eventKey={2} title={<TabTitleText>Scan</TabTitleText>}>
            <ScanTab />
          </Tab>
        </Tabs>
      </PageSection>
    </>
  );
}
