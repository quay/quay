import React, {useState, useCallback} from 'react';
import {Button, ToolbarItem} from '@patternfly/react-core';
import {ColumnsIcon} from '@patternfly/react-icons';
import ManageColumnsModal from './ManageColumnsModal';
import type {ColumnConfig} from './types';

interface ManageColumnsButtonProps {
  columns: ColumnConfig[];
  onSave: (columns: ColumnConfig[]) => void;
  maxVisibleColumns?: number;
}

export const ManageColumnsButton: React.FC<ManageColumnsButtonProps> = ({
  columns,
  onSave,
  maxVisibleColumns,
}) => {
  const [isModalOpen, setIsModalOpen] = useState(false);

  const handleOpen = useCallback(() => setIsModalOpen(true), []);
  const handleClose = useCallback(() => setIsModalOpen(false), []);

  return (
    <ToolbarItem>
      <Button
        variant="plain"
        aria-label="Manage columns"
        onClick={handleOpen}
        data-testid="manage-columns-button"
      >
        <ColumnsIcon />
      </Button>
      {isModalOpen && (
        <ManageColumnsModal
          isOpen={isModalOpen}
          onClose={handleClose}
          columns={columns}
          onSave={onSave}
          maxVisibleColumns={maxVisibleColumns}
        />
      )}
    </ToolbarItem>
  );
};

export default ManageColumnsButton;
