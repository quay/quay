import React from 'react';
import {Checkbox, Flex, FlexItem, TextInput} from '@patternfly/react-core';
import {VulnerabilityListItem} from './Types';

export function SecurityReportFilter(props: SecurityReportFilterProps) {
  const onSearchTermChanged = (
    _event: React.FormEvent<HTMLInputElement>,
    newSearchTerm: string,
  ) => {
    props.setPage(1);
    props.setSearchTerm(newSearchTerm);
  };

  const onShowOnlyFixableChanged = (
    _event: React.FormEvent<HTMLInputElement>,
    checked: boolean,
  ) => {
    props.setPage(1);
    props.setIsFixedOnlyChecked(checked);
  };

  return (
    <Flex>
      <FlexItem>
        <TextInput
          isRequired
          type="search"
          id="vulnerabilities-search"
          key="vulnerabilities-search"
          name="vulnerability-search"
          placeholder="Filter Vulnerabilities..."
          value={props.searchTerm}
          onChange={onSearchTermChanged}
        />
      </FlexItem>
      <FlexItem>
        <Checkbox
          label="Only show fixable"
          aria-label="fixable"
          id="fixable-checkbox"
          isChecked={props.isFixedOnlyChecked}
          onChange={onShowOnlyFixableChanged}
        />
      </FlexItem>
    </Flex>
  );
}

interface SecurityReportFilterProps {
  setPage: (page: number) => void;
  vulnList: VulnerabilityListItem[];
  searchTerm: string;
  setSearchTerm: (searchTerm: string) => void;
  isFixedOnlyChecked: boolean;
  setIsFixedOnlyChecked: (checked: boolean) => void;
}
