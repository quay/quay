import {Dropdown, DropdownToggle} from '@patternfly/react-core';
import * as React from 'react';

export function Kebab(props: KebabProps) {
  return (
    <Dropdown
      onSelect={() => props.setKebabOpen(!props.isKebabOpen)}
      toggle={
        <DropdownToggle
          onToggle={() => props.setKebabOpen(!props.isKebabOpen)}
          id="toggle-id-6"
        >
          Actions
        </DropdownToggle>
      }
      isOpen={props.isKebabOpen}
      dropdownItems={props.kebabItems}
    />
  );
}

type KebabProps = {
  isKebabOpen: boolean;
  setKebabOpen: (open) => void;
  kebabItems: React.ReactElement[];
};
