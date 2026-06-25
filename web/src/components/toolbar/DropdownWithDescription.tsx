import {useEffect, useRef, useState} from 'react';
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

  // Refs for callback props so the useEffect always reads fresh values
  // without re-triggering when parent recreates function/object references.
  const onSelectRef = useRef(props.onSelect);
  const onRowSelectRef = useRef(props.OnRowSelect);
  const setUserEntryRef = useRef(props.setUserEntry);
  const repoRef = useRef(props.repo);
  const rowIndexRef = useRef(props.rowIndex);
  onSelectRef.current = props.onSelect;
  onRowSelectRef.current = props.OnRowSelect;
  setUserEntryRef.current = props.setUserEntry;
  repoRef.current = props.repo;
  rowIndexRef.current = props.rowIndex;

  const dropdownOnSelect = (name, userEntry) => {
    if (!props.wizarStep) {
      props.setUserEntry(userEntry);
      if (name === defaultUnSelectedVal) {
        props.OnRowSelect(props.repo, props?.rowIndex, false);
      } else if (name !== defaultUnSelectedVal && !props?.isItemSelected) {
        props.OnRowSelect(props.repo, props?.rowIndex, true);
      }
    } else {
      if (name === defaultUnSelectedVal && props.OnRowSelect) {
        props.OnRowSelect(props.repo, props?.rowIndex, false);
      }
    }
    setDropdownToggle(name);
    props.onSelect(name, props?.repo);
    setIsOpen(false);
  };

  useEffect(() => {
    // Uses refs for callback props to avoid stale closures without
    // re-triggering the effect when parent recreates references.
    const applySelection = (name: string, userEntry: boolean) => {
      if (!props.wizarStep) {
        setUserEntryRef.current?.(userEntry);
        if (name === defaultUnSelectedVal) {
          onRowSelectRef.current?.(repoRef.current, rowIndexRef.current, false);
        } else if (name !== defaultUnSelectedVal && !props?.isItemSelected) {
          onRowSelectRef.current?.(repoRef.current, rowIndexRef.current, true);
        }
      } else {
        if (name === defaultUnSelectedVal && onRowSelectRef.current) {
          onRowSelectRef.current(repoRef.current, rowIndexRef.current, false);
        }
      }
      setDropdownToggle(name);
      onSelectRef.current(name, repoRef.current);
      setIsOpen(false);
    };

    if (props.wizarStep) {
      // Wizard step mode: always default to 'Read' when a row is selected
      if (props.selectedVal && props.selectedVal !== 'None') {
        applySelection(props.selectedVal, true);
      } else if (props?.isItemSelected) {
        // Row is selected but no permission set yet - default to 'Read'
        applySelection(defaultSelectedVal, true);
      } else if (props.selectedVal === 'None') {
        setDropdownToggle('None');
      }
      return;
    }
    // Non-wizard mode: only show actual values, be careful about defaulting
    // If we have a valid permission value, always use it first
    if (props.selectedVal && props.selectedVal !== 'None') {
      if (props.selectedVal !== dropdownToggle) {
        applySelection(props.selectedVal, props?.isUserEntry || false);
      }
      return;
    }
    // Only default to 'Read' when user manually selects a row (isUserEntry=true),
    // not when rows are auto-selected during loading of existing permissions
    if (
      props?.isItemSelected &&
      (!props.selectedVal || props.selectedVal === 'None')
    ) {
      if (props?.isUserEntry) {
        applySelection(defaultSelectedVal, true);
      }
    } else if (!props?.isItemSelected) {
      applySelection(defaultUnSelectedVal, props?.isUserEntry || false);
    }
  }, [
    props?.isItemSelected,
    props.selectedVal,
    props.wizarStep,
    props.isUserEntry,
  ]);

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
            component="button"
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
