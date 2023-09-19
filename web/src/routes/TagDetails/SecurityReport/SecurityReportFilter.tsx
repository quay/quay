import {useState} from 'react';
import {Checkbox, Flex, FlexItem, TextInput} from '@patternfly/react-core';
import {VulnerabilityListItem} from './Types';

export function SecurityReportFilter(props: SecurityReportFilterProps) {
  const [isFixedOnlyChecked, setIsFixedOnlyChecked] = useState<boolean>(false);
  const [searchTerm, setSearchTerm] = useState<string>('');

  const filterVulnList = (searchTerm: string, fixedOnlyChecked: boolean) => {
    return props.vulnList.filter((item: VulnerabilityListItem) => {
      const searchStr = item.PackageName + item.Advisory;
      return (
        searchStr.toLowerCase().includes(searchTerm.toLowerCase()) &&
        (!fixedOnlyChecked || item.FixedInVersion)
      );
    });
  };

  const onSearchTermChanged = (newSearchTerm: string) => {
    props.setPage(1);
    setSearchTerm(newSearchTerm);
    props.setFilteredVulnList(
      filterVulnList(newSearchTerm, isFixedOnlyChecked),
    );
  };

  const onShowOnlyFixableChanged = (checked: boolean) => {
    props.setPage(1);
    setIsFixedOnlyChecked(checked);
    props.setFilteredVulnList(filterVulnList(searchTerm, checked));
  };

  return (
    <Flex className="pf-v5-u-mt-md">
      <FlexItem>
        <TextInput
          isRequired
          type="search"
          id="vulnerabilities-search"
          key="vulnerabilities-search"
          name="vulnerability-search"
          placeholder="Filter Vulnerabilities..."
          value={searchTerm}
          onChange={(_event, newSearchTerm: string) =>
            onSearchTermChanged(newSearchTerm)
          }
        />
      </FlexItem>
      <FlexItem>
        <Checkbox
          label="Only show fixable"
          aria-label="fixable"
          id="fixable-checkbox"
          isChecked={isFixedOnlyChecked}
          onChange={(_event, checked: boolean) =>
            onShowOnlyFixableChanged(checked)
          }
        />
      </FlexItem>
    </Flex>
  );
}

interface SecurityReportFilterProps {
  setPage: (page: number) => void;
  vulnList: VulnerabilityListItem[];
  setFilteredVulnList: (vulnList: VulnerabilityListItem[]) => void;
}
