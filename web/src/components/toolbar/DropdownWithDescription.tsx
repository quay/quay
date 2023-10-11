import {useEffect, useState} from 'react';
import {
  Dropdown,
  DropdownItem,
  DropdownList,
  MenuToggle,
  MenuToggleElement,
} from '@patternfly/react-core';

const defaultSelectedVal = 'Read';
const defaultUnSelectedVal = 'None';

export function DropdownWithDescription(props: DropdownWithDescriptionProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [dropdownToggle, setDropdownToggle] = useState('');

  const dropdownOnSelect = (name, userEntry) => {
    if (!props.wizarStep) {
      props.setUserEntry(userEntry);
      if (name == defaultUnSelectedVal) {
        props.OnRowSelect(props.repo, props?.rowIndex, false);
      } else if (name != defaultUnSelectedVal && !props?.isItemSelected) {
        props.OnRowSelect(props.repo, props?.rowIndex, true);
      }
    }
    setDropdownToggle(name);
    props.onSelect(name, props?.repo);
    setIsOpen(false);
  };

  useEffect(() => {
    if (props.wizarStep) {
      if (props.selectedVal) {
        dropdownOnSelect(props.selectedVal, true);
      }
      return;
    }
    if (
      props?.isItemSelected &&
      (!props.selectedVal || props.selectedVal == 'None')
    ) {
      dropdownOnSelect(defaultSelectedVal, props?.isUserEntry || false);
    } else if (!props?.isItemSelected) {
      dropdownOnSelect(defaultUnSelectedVal, props?.isUserEntry || false);
    }
    if (props.selectedVal && props.selectedVal != dropdownToggle) {
      dropdownOnSelect(props.selectedVal, props?.isUserEntry || false);
    }
  }, [props?.isItemSelected, props.selectedVal]);

  return (
    <Dropdown
      data-testid={`${props.repo?.name}-permission-dropdown`}
      onSelect={() => setIsOpen(false)}
      toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
        <MenuToggle
          ref={toggleRef}
          id="toggle-descriptions"
          onClick={() => setIsOpen(() => !isOpen)}
          isExpanded={isOpen}
          data-testid={`${props.repo?.name}-permission-dropdown-toggle`}
        >
          {dropdownToggle}
        </MenuToggle>
      )}
      isOpen={isOpen}
      onOpenChange={(isOpen) => setIsOpen(isOpen)}
      shouldFocusToggleOnSelect
    >
      <DropdownList>
        {props.dropdownItems.map((item) => (
          <DropdownItem
            data-testid={`${item.name}-permission-type`}
            key={item.name}
            description={item.description}
            onClick={() => dropdownOnSelect(item.name, true)}
          >
            {item.name}
          </DropdownItem>
        ))}
      </DropdownList>
    </Dropdown>
  );
}

interface DropdownWithDescriptionProps {
  dropdownItems: any[];
  onSelect: (item, repo) => void;
  selectedVal: string;
  wizarStep: boolean;
  isItemSelected?: boolean;
  OnRowSelect?: (item, rowIndex, isSelecting) => void;
  repo?: Record<string, unknown>;
  rowIndex?: number;
  isUserEntry?: boolean;
  setUserEntry?: (userEntry) => void;
}
