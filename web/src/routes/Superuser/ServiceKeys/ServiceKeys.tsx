import {
  PageSection,
  PageSectionVariants,
  Title,
  Toolbar,
  ToolbarContent,
  ToolbarItem,
  PanelFooter,
  Dropdown,
  MenuToggle,
  DropdownList,
  DropdownItem,
  TextInput,
  Modal,
  ModalVariant,
  Button,
  Form,
  FormGroup,
} from '@patternfly/react-core';
import {
  Table,
  Tbody,
  Td,
  Th,
  Thead,
  Tr,
  ThProps,
} from '@patternfly/react-table';
import {ReactElement, useState} from 'react';
import moment from 'moment';
import {QuayBreadcrumb} from 'src/components/breadcrumb/Breadcrumb';
import {
  KeyIcon,
  ExclamationTriangleIcon,
  ClockIcon,
  CogIcon,
} from '@patternfly/react-icons';
import Empty from 'src/components/empty/Empty';
import {LoadingPage} from 'src/components/LoadingPage';

import {ToolbarButton} from 'src/components/toolbar/ToolbarButton';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';
import {DropdownCheckbox} from 'src/components/toolbar/DropdownCheckbox';
import {Kebab} from 'src/components/toolbar/Kebab';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
import {useServiceKeys} from 'src/hooks/UseServiceKeys';
import {IServiceKey} from 'src/resources/ServiceKeysResource';
import {CreateServiceKeyForm} from './CreateServiceKeyForm';
import {Navigate} from 'react-router-dom';

function ServiceKeysHeader() {
  return (
    <>
      <QuayBreadcrumb />
      <PageSection variant={PageSectionVariants.light} hasShadowBottom>
        <div className="co-m-nav-title--row">
          <Title headingLevel="h1">Service Keys</Title>
        </div>
      </PageSection>
    </>
  );
}

// Helper function to format relative time using moment.js (same as Angular am-time-ago)
// Handles both unix timestamps (numbers) and ISO date strings
function formatRelativeTime(dateValue: string | number): string {
  // Check if it's a unix timestamp (number) or ISO string
  const timeString =
    typeof dateValue === 'number'
      ? moment.unix(dateValue).fromNow()
      : moment(dateValue).fromNow();

  // Capitalize first letter to match Angular am-time-ago directive
  return timeString.charAt(0).toUpperCase() + timeString.slice(1);
}

function getApprovalStatus(key: IServiceKey): string {
  if (!key.approval) return 'Awaiting Approval';

  switch (key.approval.approval_type) {
    case 'ServiceKeyApprovalType.AUTOMATIC':
      return 'Generated Automatically';
    case 'ServiceKeyApprovalType.SUPERUSER':
      return `Approved by ${key.approval.approver?.username || 'Unknown'}`;
    case 'ServiceKeyApprovalType.KEY_ROTATION':
      return 'Approved via key rotation';
    default:
      return 'Approved';
  }
}

// Expiration status logic matching Angular implementation
function getExpirationStatus(key: IServiceKey): {
  text: string;
  icon: React.ReactElement | null;
  color: string;
} {
  if (!key.expiration_date) {
    return {text: 'Never', icon: null, color: '#aaa'};
  }

  // Create moment object handling both unix timestamps and ISO strings
  const getMomentFromDate = (dateValue: string | number) => {
    return typeof dateValue === 'number'
      ? moment.unix(dateValue)
      : moment(dateValue);
  };

  const expirationMoment = getMomentFromDate(key.expiration_date);
  const now = moment();
  const oneWeekFromNow = moment().add(1, 'week');
  const oneMonthFromNow = moment().add(1, 'month');

  if (now.isAfter(expirationMoment)) {
    // Expired - red triangle
    const timeText = getMomentFromDate(key.expiration_date).fromNow();
    return {
      text: timeText.charAt(0).toUpperCase() + timeText.slice(1),
      icon: <ExclamationTriangleIcon style={{color: '#D64456'}} />,
      color: '#D64456',
    };
  }

  if (oneWeekFromNow.isAfter(expirationMoment)) {
    // Critical (within 1 week) - orange triangle
    const timeText = getMomentFromDate(key.expiration_date).fromNow();
    return {
      text: timeText.charAt(0).toUpperCase() + timeText.slice(1),
      icon: <ExclamationTriangleIcon style={{color: '#F77454'}} />,
      color: '#F77454',
    };
  }

  if (oneMonthFromNow.isAfter(expirationMoment)) {
    // Warning (within 1 month) - orange triangle
    const timeText = getMomentFromDate(key.expiration_date).fromNow();
    return {
      text: timeText.charAt(0).toUpperCase() + timeText.slice(1),
      icon: <ExclamationTriangleIcon style={{color: '#FCA657'}} />,
      color: '#FCA657',
    };
  }

  // Info (beyond 1 month) - green circle
  const timeText = getMomentFromDate(key.expiration_date).fromNow();
  return {
    text: timeText.charAt(0).toUpperCase() + timeText.slice(1),
    icon: <ClockIcon style={{color: '#2FC98E'}} />,
    color: '#2FC98E',
  };
}

export default function ServiceKeys() {
  const {isSuperUser, loading: userLoading} = useCurrentUser();
  const {
    serviceKeys,
    paginatedKeys,
    filteredKeys,
    loading,
    error,
    refetch,
    search,
    setSearch,
    page,
    setPage,
    perPage,
    setPerPage,
    activeSortIndex,
    activeSortDirection,
    handleSort,
    bulkDeleteKeys,
    isBulkDeleting,
    updateServiceKey,
    deleteServiceKey,
    isUpdating,
    isDeleting,
  } = useServiceKeys();

  // Control expanded service keys
  const [expandedKeys, setExpandedKeys] = useState<string[]>([]);
  const setKeyExpanded = (key: IServiceKey, isExpanding = true) =>
    setExpandedKeys((prevExpanded) => {
      const otherExpandedKeys = prevExpanded.filter((k) => k !== key.kid);
      return isExpanding ? [...otherExpandedKeys, key.kid] : otherExpandedKeys;
    });
  const isKeyExpanded = (key: IServiceKey) => expandedKeys.includes(key.kid);

  // Control dropdown menus for actions
  const [openActionMenus, setOpenActionMenus] = useState<string[]>([]);
  const setActionMenuOpen = (keyId: string, isOpen: boolean) =>
    setOpenActionMenus((prevOpen) => {
      const otherOpen = prevOpen.filter((id) => id !== keyId);
      return isOpen ? [...otherOpen, keyId] : otherOpen;
    });
  const isActionMenuOpen = (keyId: string) => openActionMenus.includes(keyId);

  // Sort helper function following PatternFly pattern
  const getSortableSort = (columnIndex: number): ThProps['sort'] => ({
    sortBy: {
      index: activeSortIndex,
      direction: activeSortDirection,
    },
    onSort: handleSort,
    columnIndex,
  });

  // Selection state management
  const [selectedKeys, setSelectedKeys] = useState<string[]>([]);
  const [isKebabOpen, setKebabOpen] = useState(false);

  // Delete modal state (bulk)
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);

  // Create modal state
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  // Row-level action modals
  const [editingKey, setEditingKey] = useState<IServiceKey | null>(null);
  const [isNameModalOpen, setIsNameModalOpen] = useState(false);
  const [isExpirationModalOpen, setIsExpirationModalOpen] = useState(false);
  const [isRowDeleteModalOpen, setIsRowDeleteModalOpen] = useState(false);

  // Form data
  const [newName, setNewName] = useState('');
  const [newExpiration, setNewExpiration] = useState<string>('');

  // Selection helper functions
  const isKeySelectable = () => true; // All keys are selectable
  const isKeySelected = (key: IServiceKey) => selectedKeys.includes(key.kid);
  const setKeySelected = (key: IServiceKey, isSelecting = true) =>
    setSelectedKeys((prevSelected) => {
      const otherSelected = prevSelected.filter((k) => k !== key.kid);
      return isSelecting && isKeySelectable()
        ? [...otherSelected, key.kid]
        : otherSelected;
    });

  const onSelectKey = (
    key: IServiceKey,
    rowIndex: number,
    isSelecting: boolean,
  ) => {
    setKeySelected(key, isSelecting);
  };

  // Bulk delete handler
  const handleBulkDelete = () => {
    bulkDeleteKeys(selectedKeys);
    setSelectedKeys([]); // Clear selection after delete
    setIsDeleteModalOpen(false);
  };

  // Row-level action handlers
  const openNameModal = (key: IServiceKey) => {
    setEditingKey(key);
    setNewName(key.name || '');
    setIsNameModalOpen(true);
  };

  const openExpirationModal = (key: IServiceKey) => {
    setEditingKey(key);
    // Convert expiration to datetime-local format if it exists
    if (key.expiration_date) {
      const expDate =
        typeof key.expiration_date === 'number'
          ? new Date(key.expiration_date * 1000)
          : new Date(key.expiration_date);
      // Format as YYYY-MM-DDTHH:MM for datetime-local input
      const year = expDate.getFullYear();
      const month = String(expDate.getMonth() + 1).padStart(2, '0');
      const day = String(expDate.getDate()).padStart(2, '0');
      const hours = String(expDate.getHours()).padStart(2, '0');
      const minutes = String(expDate.getMinutes()).padStart(2, '0');
      setNewExpiration(`${year}-${month}-${day}T${hours}:${minutes}`);
    } else {
      setNewExpiration('');
    }
    setIsExpirationModalOpen(true);
  };

  const openRowDeleteModal = (key: IServiceKey) => {
    setEditingKey(key);
    setIsRowDeleteModalOpen(true);
  };

  const handleUpdateName = () => {
    if (editingKey) {
      updateServiceKey(editingKey.kid, {name: newName});
      setIsNameModalOpen(false);
      setEditingKey(null);
    }
  };

  const handleUpdateExpiration = () => {
    if (editingKey) {
      const expirationTimestamp = newExpiration
        ? Math.floor(new Date(newExpiration).getTime() / 1000)
        : null;
      updateServiceKey(editingKey.kid, {expiration: expirationTimestamp});
      setIsExpirationModalOpen(false);
      setEditingKey(null);
    }
  };

  const handleRowDelete = () => {
    if (editingKey) {
      deleteServiceKey(editingKey.kid);
      setIsRowDeleteModalOpen(false);
      setEditingKey(null);
    }
  };

  // Bulk actions (matching actual Angular behavior - only delete works)
  const kebabItems: ReactElement[] = [
    <DropdownItem
      key="delete-keys"
      onClick={() => setIsDeleteModalOpen(true)}
      data-testid="bulk-delete-keys"
    >
      Delete Keys
    </DropdownItem>,
  ];

  if (userLoading || loading) {
    return <LoadingPage />;
  }

  // Redirect non-superusers
  if (!isSuperUser) {
    return <Navigate to="/organization" replace />;
  }

  if (error) {
    return (
      <>
        <ServiceKeysHeader />
        <PageSection>
          <div>
            Error loading service keys:{' '}
            {error instanceof Error ? error.message : 'Unknown error'}
          </div>
        </PageSection>
      </>
    );
  }

  return (
    <>
      <ServiceKeysHeader />
      <PageSection>
        <div style={{marginBottom: '20px'}}>
          Service keys provide a recognized means of authentication between Quay
          and external services, as well as between external services. <br />
          Example services include Quay Security Scanner speaking to a{' '}
          <a
            href="https://docs.projectquay.io/manage_quay.html#clair-v4"
            target="_blank"
            rel="noopener noreferrer"
          >
            Clair
          </a>{' '}
          cluster, or Quay speaking to its{' '}
          <a
            href="https://docs.projectquay.io/use_quay.html#build-support"
            target="_blank"
            rel="noopener noreferrer"
          >
            build workers
          </a>
          .
        </div>

        {/* Toolbar */}
        <Toolbar>
          <ToolbarContent>
            <DropdownCheckbox
              selectedItems={selectedKeys}
              deSelectAll={setSelectedKeys}
              allItemsList={filteredKeys}
              itemsPerPageList={paginatedKeys}
              onItemSelect={onSelectKey}
              id="service-keys-checkbox"
            />
            <ToolbarItem variant="search-filter">
              <TextInput
                type="search"
                id="service-keys-search-input"
                name="service-keys-search"
                data-testid="service-keys-search"
                placeholder="Filter Keys..."
                value={search.query}
                onChange={(_event, val) =>
                  setSearch((prev) => ({...prev, query: val.trim()}))
                }
              />
            </ToolbarItem>
            <ToolbarButton
              id="create-service-key-button"
              data-testid="create-service-key-button"
              buttonValue="Create Preshareable Key"
              Modal={<div />}
              isModalOpen={isCreateModalOpen}
              setModalOpen={setIsCreateModalOpen}
            />
            <ToolbarItem>
              {selectedKeys.length > 0 && (
                <Kebab
                  isKebabOpen={isKebabOpen}
                  setKebabOpen={setKebabOpen}
                  kebabItems={kebabItems}
                  useActions={true}
                  data-testid="bulk-actions-kebab"
                />
              )}
            </ToolbarItem>
            <ToolbarPagination
              itemsList={filteredKeys}
              perPage={perPage}
              page={page}
              setPage={setPage}
              setPerPage={setPerPage}
              total={filteredKeys.length}
            />
          </ToolbarContent>
        </Toolbar>

        {!loading && !serviceKeys?.length ? (
          <Empty
            title="No service keys defined"
            icon={KeyIcon}
            body="There are no keys defined for working with external services"
          />
        ) : (
          <>
            <Table aria-label="Service keys table" variant="compact">
              <Thead>
                <Tr>
                  <Th />
                  <Th />
                  <Th modifier="wrap" sort={getSortableSort(2)}>
                    Name
                  </Th>
                  <Th modifier="wrap" sort={getSortableSort(3)}>
                    Service Name
                  </Th>
                  <Th modifier="wrap" sort={getSortableSort(4)}>
                    Created
                  </Th>
                  <Th modifier="wrap" sort={getSortableSort(5)}>
                    Expires
                  </Th>
                  <Th modifier="wrap">Approval Status</Th>
                  <Th modifier="wrap">Actions</Th>
                </Tr>
              </Thead>
              {paginatedKeys.map((key, rowIndex) => {
                const expiration = getExpirationStatus(key);
                return (
                  <Tbody key={key.kid} isExpanded={isKeyExpanded(key)}>
                    <Tr>
                      <Td
                        expand={{
                          rowIndex,
                          isExpanded: isKeyExpanded(key),
                          onToggle: () =>
                            setKeyExpanded(key, !isKeyExpanded(key)),
                        }}
                      />
                      <Td
                        select={{
                          rowIndex,
                          onSelect: (_event, isSelecting) =>
                            onSelectKey(key, rowIndex, isSelecting),
                          isSelected: isKeySelected(key),
                          isDisabled: !isKeySelectable(),
                        }}
                        data-testid={`select-${key.kid}`}
                      />
                      <Td dataLabel="Name">
                        <a
                          href="#"
                          style={{color: '#007acc'}}
                          data-testid={`expand-${key.kid}`}
                          onClick={(e) => {
                            e.preventDefault();
                            setKeyExpanded(key, !isKeyExpanded(key));
                          }}
                        >
                          {key.name || '(Unnamed)'}
                        </a>
                      </Td>
                      <Td dataLabel="Service Name">{key.service}</Td>
                      <Td dataLabel="Created">
                        {formatRelativeTime(key.created_date)}
                      </Td>
                      <Td dataLabel="Expires" style={{color: expiration.color}}>
                        {expiration.icon && (
                          <span
                            style={{
                              marginRight: '6px',
                              display: 'inline-block',
                            }}
                          >
                            {expiration.icon}
                          </span>
                        )}
                        {expiration.text}
                      </Td>
                      <Td dataLabel="Approval Status">
                        {getApprovalStatus(key)}
                      </Td>
                      <Td dataLabel="Actions">
                        <Dropdown
                          toggle={(toggleRef) => (
                            <MenuToggle
                              ref={toggleRef}
                              id={`${key.kid}-actions-toggle`}
                              data-testid={`${key.kid}-actions-toggle`}
                              variant="plain"
                              onClick={() =>
                                setActionMenuOpen(
                                  key.kid,
                                  !isActionMenuOpen(key.kid),
                                )
                              }
                              isExpanded={isActionMenuOpen(key.kid)}
                            >
                              <CogIcon />
                            </MenuToggle>
                          )}
                          isOpen={isActionMenuOpen(key.kid)}
                          onOpenChange={(isOpen) =>
                            setActionMenuOpen(key.kid, isOpen)
                          }
                          popperProps={{
                            enableFlip: true,
                            position: 'right',
                          }}
                        >
                          <DropdownList>
                            <DropdownItem onClick={() => openNameModal(key)}>
                              Set Friendly Name
                            </DropdownItem>
                            <DropdownItem
                              onClick={() => openExpirationModal(key)}
                            >
                              Change Expiration Time
                            </DropdownItem>
                            <DropdownItem
                              onClick={() => openRowDeleteModal(key)}
                            >
                              Delete Key
                            </DropdownItem>
                          </DropdownList>
                        </Dropdown>
                      </Td>
                    </Tr>
                    <Tr isExpanded={isKeyExpanded(key)}>
                      <Td colSpan={8}>
                        <div
                          style={{padding: '16px 0'}}
                          data-testid={`key-details-${key.kid}`}
                        >
                          <div
                            style={{
                              fontWeight: 'bold',
                              marginBottom: '8px',
                              fontSize: '12px',
                              textTransform: 'uppercase',
                              color: '#6a6e73',
                            }}
                          >
                            Full Key ID
                          </div>
                          <div
                            style={{
                              fontFamily: 'monospace',
                              fontSize: '14px',
                            }}
                          >
                            {key.kid}
                          </div>
                        </div>
                      </Td>
                    </Tr>
                  </Tbody>
                );
              })}
            </Table>
            <PanelFooter>
              <ToolbarPagination
                itemsList={filteredKeys}
                perPage={perPage}
                page={page}
                setPage={setPage}
                setPerPage={setPerPage}
                total={filteredKeys.length}
                bottom={true}
              />
            </PanelFooter>
          </>
        )}
      </PageSection>

      {/* Create Service Key Modal */}
      <CreateServiceKeyForm
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={() => {
          // Refresh the service keys data
          refetch();
        }}
      />

      {/* Bulk Delete Confirmation Modal */}
      <Modal
        variant={ModalVariant.small}
        title="Delete Service Keys?"
        titleIconVariant="warning"
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        data-testid="bulk-delete-modal"
        actions={[
          <Button
            key="delete"
            variant="danger"
            onClick={handleBulkDelete}
            isLoading={isBulkDeleting}
            isDisabled={isBulkDeleting}
            data-testid="confirm-bulk-delete"
          >
            Delete
          </Button>,
          <Button
            key="cancel"
            variant="link"
            onClick={() => setIsDeleteModalOpen(false)}
            isDisabled={isBulkDeleting}
          >
            Cancel
          </Button>,
        ]}
      >
        <p>
          Are you sure you want to delete the following{' '}
          <strong>{selectedKeys.length}</strong> service key
          {selectedKeys.length === 1 ? '' : 's'}? This action cannot be undone.
        </p>
        <div style={{marginTop: '1rem'}}>
          {selectedKeys.map((keyId) => {
            const key = serviceKeys.find((k) => k.kid === keyId);
            return (
              <div key={keyId} style={{marginBottom: '0.5rem'}}>
                <strong>{key?.name || '(Unnamed)'}</strong> - {key?.service}
              </div>
            );
          })}
        </div>
      </Modal>

      {/* Set Friendly Name Modal */}
      <Modal
        variant={ModalVariant.small}
        title="Set Friendly Name"
        isOpen={isNameModalOpen}
        onClose={() => setIsNameModalOpen(false)}
        data-testid="set-name-modal"
        actions={[
          <Button
            key="save"
            variant="primary"
            data-testid="save-name-button"
            onClick={handleUpdateName}
            isLoading={isUpdating}
            isDisabled={isUpdating}
          >
            Save
          </Button>,
          <Button
            key="cancel"
            variant="link"
            onClick={() => setIsNameModalOpen(false)}
            isDisabled={isUpdating}
          >
            Cancel
          </Button>,
        ]}
      >
        <Form>
          <FormGroup label="Friendly Name" fieldId="name-input">
            <TextInput
              id="name-input"
              data-testid="friendly-name-input"
              type="text"
              value={newName}
              onChange={(_event, value) => setNewName(value)}
              placeholder="Enter a friendly name for this key"
            />
          </FormGroup>
        </Form>
      </Modal>

      {/* Change Expiration Time Modal */}
      <Modal
        variant={ModalVariant.small}
        title="Change Service Key Expiration"
        isOpen={isExpirationModalOpen}
        onClose={() => setIsExpirationModalOpen(false)}
        data-testid="change-expiration-modal"
        actions={[
          <Button
            key="save"
            variant="primary"
            data-testid="save-expiration-button"
            onClick={handleUpdateExpiration}
            isLoading={isUpdating}
            isDisabled={isUpdating}
          >
            Change Expiration
          </Button>,
          <Button
            key="cancel"
            variant="link"
            onClick={() => setIsExpirationModalOpen(false)}
            isDisabled={isUpdating}
          >
            Cancel
          </Button>,
        ]}
      >
        <Form>
          <FormGroup label="Expiration Date:" fieldId="expiration-input">
            <div style={{display: 'flex', gap: '12px', alignItems: 'center'}}>
              <TextInput
                id="expiration-input"
                data-testid="expiration-date-input"
                type="datetime-local"
                value={newExpiration}
                onChange={(_event, value) => setNewExpiration(value)}
                placeholder="Select date and time"
                style={{flex: 1}}
              />
              <Button
                variant="link"
                onClick={() => setNewExpiration('')}
                style={{padding: '6px 8px', fontSize: '12px'}}
              >
                Clear
              </Button>
            </div>
            <div style={{fontSize: '12px', color: '#6c757d', marginTop: '8px'}}>
              If specified, the date and time that the key expires. It is highly
              recommended to have an expiration date.
            </div>
          </FormGroup>
          {/* {editingKey && (
            <div
              style={{
                marginTop: '16px',
                padding: '12px',
                backgroundColor: '#f8f9fa',
                borderRadius: '4px',
              }}
            >
              <strong>Editing:</strong> {editingKey.name || '(Unnamed)'} -{' '}
              {editingKey.service}
            </div>
          )} */}
        </Form>
      </Modal>

      {/* Row Delete Confirmation Modal */}
      <Modal
        variant={ModalVariant.small}
        title="Delete Service Key?"
        titleIconVariant="warning"
        isOpen={isRowDeleteModalOpen}
        onClose={() => setIsRowDeleteModalOpen(false)}
        data-testid="delete-service-key-modal"
        actions={[
          <Button
            key="delete"
            variant="danger"
            data-testid="confirm-delete-button"
            onClick={handleRowDelete}
            isLoading={isDeleting}
            isDisabled={isDeleting}
          >
            Delete
          </Button>,
          <Button
            key="cancel"
            variant="link"
            onClick={() => setIsRowDeleteModalOpen(false)}
            isDisabled={isDeleting}
          >
            Cancel
          </Button>,
        ]}
      >
        <p>
          Are you sure you want to delete the service key{' '}
          <strong>{editingKey?.name || '(Unnamed)'}</strong> for service{' '}
          <strong>{editingKey?.service}</strong>? This action cannot be undone.
        </p>
      </Modal>
    </>
  );
}
