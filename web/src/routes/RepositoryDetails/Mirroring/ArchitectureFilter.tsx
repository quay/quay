import React, {useState} from 'react';
import {
  FormGroup,
  Select,
  SelectOption,
  SelectList,
  MenuToggle,
  MenuToggleElement,
  Badge,
  FormHelperText,
  HelperText,
  HelperTextItem,
} from '@patternfly/react-core';

// Available architectures matching the backend validation
// See data/model/repo_mirror.py:VALID_ARCHITECTURES
const AVAILABLE_ARCHITECTURES = [
  {value: 'amd64', label: 'AMD64 (x86_64)'},
  {value: 'arm64', label: 'ARM64 (aarch64)'},
  {value: 'ppc64le', label: 'PowerPC 64 LE'},
  {value: 's390x', label: 'IBM Z (s390x)'},
];

interface ArchitectureFilterProps {
  selectedArchitectures: string[];
  onChange: (archs: string[]) => void;
  isDisabled?: boolean;
}

export const ArchitectureFilter: React.FC<ArchitectureFilterProps> = ({
  selectedArchitectures,
  onChange,
  isDisabled = false,
}) => {
  const [isOpen, setIsOpen] = useState(false);

  const onToggle = () => {
    setIsOpen(!isOpen);
  };

  const onSelect = (
    _event: React.MouseEvent<Element, MouseEvent> | undefined,
    value: string | number | undefined,
  ) => {
    const arch = value as string;
    if (selectedArchitectures.includes(arch)) {
      // Remove the architecture
      onChange(selectedArchitectures.filter((a) => a !== arch));
    } else {
      // Add the architecture
      onChange([...selectedArchitectures, arch]);
    }
    // Keep the dropdown open for multi-select
    setIsOpen(true);
  };

  const clearSelection = () => {
    onChange([]);
    setIsOpen(false);
  };

  // Generate the toggle text based on selection
  const getToggleText = () => {
    if (selectedArchitectures.length === 0) {
      return 'All architectures';
    }
    return selectedArchitectures
      .map(
        (arch) =>
          AVAILABLE_ARCHITECTURES.find((a) => a.value === arch)?.value || arch,
      )
      .join(', ');
  };

  return (
    <FormGroup
      label="Architecture Filter"
      fieldId="architecture_filter"
      isStack
    >
      <Select
        id="architecture-filter-select"
        data-testid="architecture-filter-select"
        aria-label="Select architectures to mirror"
        isOpen={isOpen}
        onOpenChange={(isOpen) => setIsOpen(isOpen)}
        onSelect={onSelect}
        toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
          <MenuToggle
            ref={toggleRef}
            onClick={onToggle}
            isExpanded={isOpen}
            isDisabled={isDisabled}
            data-testid="architecture-filter-toggle"
            style={{width: '100%'}}
          >
            {getToggleText()}
            {selectedArchitectures.length > 0 && (
              <>
                {' '}
                <Badge isRead data-testid="architecture-filter-badge">
                  {selectedArchitectures.length}
                </Badge>
              </>
            )}
          </MenuToggle>
        )}
      >
        <SelectList data-testid="architecture-filter-list">
          {AVAILABLE_ARCHITECTURES.map((arch) => (
            <SelectOption
              key={arch.value}
              value={arch.value}
              hasCheckbox
              isSelected={selectedArchitectures.includes(arch.value)}
              data-testid={`architecture-option-${arch.value}`}
            >
              {arch.label}
            </SelectOption>
          ))}
          {selectedArchitectures.length > 0 && (
            <SelectOption
              key="clear-all"
              value="clear-all"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                clearSelection();
              }}
              data-testid="architecture-clear-all"
            >
              Clear all
            </SelectOption>
          )}
        </SelectList>
      </Select>
      <FormHelperText>
        <HelperText>
          <HelperTextItem data-testid="architecture-filter-helper">
            {selectedArchitectures.length === 0
              ? 'All architectures will be mirrored from multi-arch images.'
              : `Only ${selectedArchitectures.join(
                  ', ',
                )} architecture(s) will be mirrored.`}
          </HelperTextItem>
        </HelperText>
      </FormHelperText>
    </FormGroup>
  );
};

export default ArchitectureFilter;
