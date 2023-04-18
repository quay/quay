import {
  ToggleGroup,
  ToggleGroupItem,
  ToggleGroupItemProps,
  ToolbarItem,
} from '@patternfly/react-core';
import React from 'react';

type TableModeType = 'Expand' | 'Collapse';

export function ExpandCollapseButton(props: ExpandCollapseButtonProps) {
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
      <ToggleGroup
        aria-label="Default with single selectable"
        id="expand-collapse-tab"
      >
        <ToggleGroupItem
          text="Expand"
          buttonId="Expand"
          isSelected={tableMode === 'Expand'}
          onChange={onTableModeChange}
          id="expand-tab"
        />
        <ToggleGroupItem
          text="Collapse"
          buttonId="Collapse"
          isSelected={tableMode === 'Collapse'}
          onChange={onTableModeChange}
          id="collapse-tab"
        />
      </ToggleGroup>
    </ToolbarItem>
  );
}

type ExpandCollapseButtonProps = {
  expandTable: () => void;
  collapseTable: () => void;
};
