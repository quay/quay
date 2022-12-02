import {
  ToggleGroup,
  ToggleGroupItem,
  ToggleGroupItemProps,
  ToolbarItem,
} from '@patternfly/react-core';
import React from 'react';

type TableModeType = 'All' | 'Selected';

export function AllSelectedToggleButton(props: AllSelectedToggleButtonProps) {
  const [tableMode, setTableMode] = React.useState<TableModeType>('All');

  const onTableModeChange: ToggleGroupItemProps['onChange'] = (
    _isSelected,
    event,
  ) => {
    const id = event.currentTarget.id;
    setTableMode(id as TableModeType);
    if (id == 'All') {
      props.showAllItems();
    } else if (id == 'Selected') {
      props.showSelectedItems();
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

type AllSelectedToggleButtonProps = {
  showAllItems: () => void;
  showSelectedItems: () => void;
};
