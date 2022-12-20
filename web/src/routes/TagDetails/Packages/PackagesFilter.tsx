import {useState} from 'react';
import {Flex, FlexItem, SearchInput} from '@patternfly/react-core';
import {PackagesListItem} from './Types';

export function PackagesFilter(props: PackagesFilterProps) {
  const [searchTerm, setSearchTerm] = useState<string>('');

  const filterPackagesList = (searchTerm: string) => {
    return props.packagesList.filter((item: PackagesListItem) => {
      const searchStr = item.PackageName + item.CurrentVersion;
      return searchStr.toLowerCase().includes(searchTerm.toLowerCase());
    });
  };

  const onSearchTermChanged = (newSearchTerm: string) => {
    props.setPage(1);
    setSearchTerm(newSearchTerm);
    props.setFilteredPackageList(filterPackagesList(newSearchTerm));
  };

  return (
    <Flex className="pf-u-mt-md">
      <FlexItem>
        <SearchInput
          placeholder="Filter Packages..."
          value={searchTerm}
          onChange={onSearchTermChanged}
          onClear={() => onSearchTermChanged('')}
        />
      </FlexItem>
    </Flex>
  );
}

interface PackagesFilterProps {
  setPage: (page: number) => void;
  packagesList: PackagesListItem[];
  setFilteredPackageList: (packageList: PackagesListItem[]) => void;
}
