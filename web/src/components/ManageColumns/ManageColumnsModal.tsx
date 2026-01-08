import React, {useState, useMemo, useCallback, useEffect} from 'react';
import {
  Modal,
  ModalVariant,
  Button,
  Alert,
  Split,
  SplitItem,
  DataList,
  DataListItem,
  DataListItemRow,
  DataListItemCells,
  DataListCell,
  DataListCheck,
  Title,
  Divider,
} from '@patternfly/react-core';
import type {ColumnConfig, ManageColumnsModalProps} from './types';

const MAX_COLUMNS = 9;

export const ManageColumnsModal: React.FC<ManageColumnsModalProps> = ({
  isOpen,
  onClose,
  columns,
  onSave,
  maxVisibleColumns = MAX_COLUMNS,
  title = 'Manage columns',
}) => {
  // Local state for editing (only committed on Save)
  const [editedColumns, setEditedColumns] = useState<ColumnConfig[]>(columns);

  // Reset local state when modal opens
  useEffect(() => {
    if (isOpen) {
      setEditedColumns(columns);
    }
  }, [isOpen, columns]);

  // Separate columns into default and additional
  const {defaultColumns, additionalColumns} = useMemo(() => {
    const defaults = editedColumns.filter((col) => col.isDefault);
    const additional = editedColumns.filter((col) => !col.isDefault);
    return {defaultColumns: defaults, additionalColumns: additional};
  }, [editedColumns]);

  const visibleCount = useMemo(
    () => editedColumns.filter((c) => c.isVisible).length,
    [editedColumns],
  );

  const isAtMaxColumns = visibleCount >= maxVisibleColumns;

  // Toggle column visibility
  const handleToggle = useCallback(
    (columnId: string) => {
      setEditedColumns((prev) =>
        prev.map((col) => {
          if (col.id !== columnId || col.isDisabled) {
            return col;
          }
          // Prevent enabling more columns if at max
          if (!col.isVisible && isAtMaxColumns) {
            return col;
          }
          return {...col, isVisible: !col.isVisible};
        }),
      );
    },
    [isAtMaxColumns],
  );

  // Restore defaults - make all default columns visible, hide additional
  const handleRestoreDefaults = useCallback(() => {
    setEditedColumns((prev) =>
      prev.map((col) => ({
        ...col,
        isVisible: col.isDefault || col.isDisabled,
      })),
    );
  }, []);

  // Save and close
  const handleSave = useCallback(() => {
    onSave(editedColumns);
    onClose();
  }, [editedColumns, onSave, onClose]);

  // Cancel without saving
  const handleCancel = useCallback(() => {
    onClose();
  }, [onClose]);

  // Render column list section
  const renderColumnList = (
    columnList: ColumnConfig[],
    sectionTitle: string,
  ) => (
    <div style={{flex: 1, minWidth: '200px'}}>
      <Title headingLevel="h4" size="md" style={{marginBottom: '16px'}}>
        {sectionTitle}
      </Title>
      {columnList.length === 0 ? (
        <div style={{color: 'var(--pf-v5-global--Color--200)'}}>
          No columns in this section
        </div>
      ) : (
        <DataList aria-label={`${sectionTitle} columns`} isCompact>
          {columnList.map((column) => {
            // Disable checkbox if column is disabled OR if at max and trying to enable
            const isCheckboxDisabled =
              column.isDisabled || (!column.isVisible && isAtMaxColumns);

            return (
              <DataListItem
                key={column.id}
                aria-labelledby={`column-${column.id}`}
              >
                <DataListItemRow>
                  <DataListCheck
                    aria-labelledby={`column-${column.id}`}
                    name={`column-${column.id}`}
                    checked={column.isVisible}
                    isDisabled={isCheckboxDisabled}
                    onChange={() => handleToggle(column.id)}
                  />
                  <DataListItemCells
                    dataListCells={[
                      <DataListCell key={column.id}>
                        <span id={`column-${column.id}`}>{column.title}</span>
                        {column.isDisabled && (
                          <span
                            style={{
                              color: 'var(--pf-v5-global--Color--200)',
                              marginLeft: '8px',
                            }}
                          >
                            (Required)
                          </span>
                        )}
                      </DataListCell>,
                    ]}
                  />
                </DataListItemRow>
              </DataListItem>
            );
          })}
        </DataList>
      )}
    </div>
  );

  return (
    <Modal
      variant={ModalVariant.medium}
      title={title}
      description="Selected columns will appear in the table."
      isOpen={isOpen}
      onClose={handleCancel}
      actions={[
        <Button
          key="save"
          variant="primary"
          onClick={handleSave}
          data-testid="manage-columns-save"
        >
          Save
        </Button>,
        <Button
          key="cancel"
          variant="link"
          onClick={handleCancel}
          data-testid="manage-columns-cancel"
        >
          Cancel
        </Button>,
      ]}
    >
      <Alert
        variant="info"
        isInline
        title={`You can select up to ${maxVisibleColumns} columns`}
        style={{marginBottom: '16px'}}
      />

      <Split hasGutter>
        <SplitItem isFilled>
          {renderColumnList(defaultColumns, 'Default columns')}
        </SplitItem>
        <Divider orientation={{default: 'vertical'}} />
        <SplitItem isFilled>
          {renderColumnList(additionalColumns, 'Additional columns')}
        </SplitItem>
      </Split>

      <div style={{marginTop: '24px'}}>
        <Button
          variant="link"
          onClick={handleRestoreDefaults}
          data-testid="manage-columns-restore"
        >
          Restore default columns
        </Button>
      </div>
    </Modal>
  );
};

export default ManageColumnsModal;
