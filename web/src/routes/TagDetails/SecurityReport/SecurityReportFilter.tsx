import {useState} from 'react';
import {Checkbox, Flex, FlexItem, TextInput} from '@patternfly/react-core';
import {VulnerabilityListItem} from './Types';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';

export function SecurityReportFilter(props: SecurityReportFilterProps) {
  const config = useQuayConfig();
  const [isFixedOnlyChecked, setIsFixedOnlyChecked] = useState<boolean>(false);
  const [isShowSuppressedChecked, setShowSuppressedChecked] =
    useState<boolean>(false);
  const [searchTerm, setSearchTerm] = useState<string>('');

  const filterVulnList = (
    searchTerm: string,
    fixedOnlyChecked: boolean,
    showSuppressedChecked: boolean,
  ) => {
    return props.vulnList.filter((item: VulnerabilityListItem) => {
      const searchStr = item.PackageName + item.Advisory;
      return (
        searchStr.toLowerCase().includes(searchTerm.toLowerCase()) &&
        (!fixedOnlyChecked || item.FixedInVersion) &&
        (showSuppressedChecked || !item.SuppressedBy)
      );
    });
  };

  const onSearchTermChanged = (
    _event: React.FormEvent<HTMLInputElement>,
    newSearchTerm: string,
  ) => {
    props.setPage(1);
    setSearchTerm(newSearchTerm);
    props.setFilteredVulnList(
      filterVulnList(
        newSearchTerm,
        isFixedOnlyChecked,
        isShowSuppressedChecked,
      ),
    );
  };

  const onShowOnlyFixableChanged = (
    _event: React.FormEvent<HTMLInputElement>,
    checked: boolean,
  ) => {
    props.setPage(1);
    setIsFixedOnlyChecked(checked);
    props.setFilteredVulnList(
      filterVulnList(searchTerm, checked, isShowSuppressedChecked),
    );
  };

  const onShowSuppressedChanged = (checked: boolean) => {
    props.setPage(1);
    setShowSuppressedChecked(checked);
    props.setFilteredVulnList(
      filterVulnList(searchTerm, isFixedOnlyChecked, checked),
    );
  };

  return (
    <Flex className="pf-v5-u-mt-md" alignItems={{default: 'alignItemsCenter'}}>
      <FlexItem>
        <TextInput
          isRequired
          type="search"
          id="vulnerabilities-search"
          key="vulnerabilities-search"
          name="vulnerability-search"
          placeholder="Filter Vulnerabilities..."
          value={searchTerm}
          onChange={onSearchTermChanged}
        />
      </FlexItem>
      <FlexItem>
        <Checkbox
          label="Only show fixable"
          aria-label="fixable"
          id="fixable-checkbox"
          isChecked={isFixedOnlyChecked}
          onChange={onShowOnlyFixableChanged}
        />
      </FlexItem>
      {config?.features.SECURITY_VULNERABILITY_SUPPRESSION ? (
        <FlexItem>
          <Checkbox
            label="Show suppressed"
            aria-label="suppressed"
            id="suppressed-checkbox"
            isChecked={isShowSuppressedChecked}
            onChange={(
              _event: React.FormEvent<HTMLInputElement>,
              checked: boolean,
            ) => {
              onShowSuppressedChanged(checked);
            }}
          />
        </FlexItem>
      ) : null}
    </Flex>
  );
}

interface SecurityReportFilterProps {
  setPage: (page: number) => void;
  vulnList: VulnerabilityListItem[];
  setFilteredVulnList: (vulnList: VulnerabilityListItem[]) => void;
}
