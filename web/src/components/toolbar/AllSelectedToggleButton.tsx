import {
  ToggleGroup,
  ToggleGroupItem,
  ToggleGroupItemProps,
  ToolbarItem,
} from '@patternfly/react-core';
import React from 'react';

type TableModeType = 'All' | 'Selected';

export function AllSelectedToggleButton(props: ExpandCollapseButtonProps) {
  const [tableMode, setTableMode] = React.useState<TableModeType>('Collapse');

  const onTableModeChange: ToggleGroupItemProps['onChange'] = (
    _isSelected,
    event,
  ) => {
    const id = event.currentTarget.id;
    setTableMode(id as TableModeType);
    if (id == 'Expand') {
      props.expandTable();
    } else if (id == 'Collapse') {
      props.collapseTable();
    }
  };

  return (
    <ToolbarItem>
      <ToggleGroup aria-label="Default with single selectable">
        <ToggleGroupItem
          text="All"
          buttonId="All"
          isSelected={tableMode === 'All'}
          onChange={onTableModeChange}
        />
        <ToggleGroupItem
          text="Selected"
          buttonId="Selected"
          isSelected={tableMode === 'Selected'}
          onChange={onTableModeChange}
        />
      </ToggleGroup>
    </ToolbarItem>
  );
}

type ExpandCollapseButtonProps = {
  expandTable: () => void;
  collapseTable: () => void;
};
