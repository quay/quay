import React from 'react';
import {
  Dropdown,
  DropdownList,
  MenuToggle,
  MenuToggleElement,
} from '@patternfly/react-core';
import EllipsisVIcon from '@patternfly/react-icons/dist/esm/icons/ellipsis-v-icon';

export function Kebab(props: KebabProps) {
  return (
    <Dropdown
      onSelect={() => props.setKebabOpen(!props.isKebabOpen)}
      toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
        <MenuToggle
          ref={toggleRef}
          id={props?.id}
          variant={props.useActions ? 'secondary' : 'plain'}
          onClick={() => props.setKebabOpen(!props.isKebabOpen)}
          isExpanded={props.isKebabOpen}
        >
          {props.useActions ? 'Actions' : <EllipsisVIcon />}
        </MenuToggle>
      )}
      isOpen={props.isKebabOpen}
      isPlain={!props.useActions}
      onOpenChange={(isOpen) => props.setKebabOpen(isOpen)}
      shouldFocusToggleOnSelect
    >
      <DropdownList>{props.kebabItems}</DropdownList>
    </Dropdown>
  );
}

type KebabProps = {
  isKebabOpen: boolean;
  setKebabOpen: (open) => void;
  kebabItems: React.ReactElement[];
  useActions?: boolean;
  id?: string;
};
