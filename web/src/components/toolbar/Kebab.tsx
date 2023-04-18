import {Dropdown, DropdownToggle, KebabToggle} from '@patternfly/react-core';
import * as React from 'react';

export function Kebab(props: KebabProps) {
  const onToggle = () => {
    props.setKebabOpen(!props.isKebabOpen);
  };

  const fetchToggle = () => {
    if (!props.useActions) {
      return <KebabToggle onToggle={onToggle} />;
    }
    return (
      <DropdownToggle
        onToggle={() => props.setKebabOpen(!props.isKebabOpen)}
        id="toggle-id-6"
      >
        Actions
      </DropdownToggle>
    );
  };

  return (
    <Dropdown
      onSelect={() => props.setKebabOpen(!props.isKebabOpen)}
      toggle={fetchToggle()}
      isOpen={props.isKebabOpen}
      dropdownItems={props.kebabItems}
      isPlain={!props.useActions}
    />
  );
}

type KebabProps = {
  isKebabOpen: boolean;
  setKebabOpen: (open) => void;
  kebabItems: React.ReactElement[];
  useActions?: boolean;
};
