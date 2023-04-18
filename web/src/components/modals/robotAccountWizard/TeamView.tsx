import {
  TableComposable,
  Tbody,
  Td,
  Th,
  Thead,
  Tr,
} from '@patternfly/react-table';
import {
  PageSection,
  PanelFooter,
  ToggleGroup,
  ToggleGroupItem,
  ToggleGroupItemProps,
  Toolbar,
  ToolbarContent,
  ToolbarItem,
} from '@patternfly/react-core';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';
import {useRecoilState} from 'recoil';
import {searchTeamState} from 'src/atoms/TeamState';
import React, {useEffect, useState} from 'react';
import {DropdownCheckbox} from 'src/components/toolbar/DropdownCheckbox';
import {FilterWithDropdown} from 'src/components/toolbar/FilterWithDropdown';
import {formatDate} from 'src/libs/utils';
import {FilterInput} from 'src/components/toolbar/FilterInput';

const ColumnNames = {
  name: 'Team',
  role: 'Role',
  members: 'Members',
  lastUpdated: 'Last Updated',
};

type TableModeType = 'All' | 'Selected';

export default function TeamView(props: TeamViewProps) {
  const [tableMode, setTableMode] = useState<TableModeType>('All');
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(10);
  const [tableItems, setTableItems] = useState([]);
  const [search, setSearch] = useRecoilState(searchTeamState);
  const [searchInputText, setSearchInputText] = useState('Search, create team');

  useEffect(() => {
    if (tableMode == 'All') {
      setTableItems(props.items);
    } else if (tableMode == 'Selected') {
      setTableItems(props.selectedTeams);
    }
    if (props.searchInputText) {
      setSearchInputText(props.searchInputText);
    }
  });

  const filteredItems =
    search.query !== ''
      ? tableItems?.filter((item) => {
          const Itemname = item.name;
          return Itemname.includes(search.query);
        })
      : tableItems;

  const paginatedItems = filteredItems?.slice(
    page * perPage - perPage,
    page * perPage - perPage + perPage,
  );

  const onTableModeChange: ToggleGroupItemProps['onChange'] = (
    _isSelected,
    event,
  ) => {
    const id = event.currentTarget.id;
    setTableMode(id as TableModeType);
  };

  const setItemSelected = (item, isSelecting = true) => {
    props.setSelectedTeams((prevSelected) => {
      const otherSelectedItems = prevSelected.filter(
        (r) => r.name !== item.name,
      );
      return isSelecting ? [...otherSelectedItems, item] : otherSelectedItems;
    });
  };

  // Logic for handling row-wise checkbox selection in <Td>
  const isItemSelected = (item) => props.selectedTeams?.includes(item);

  const onSelectItem = (item, rowIndex: number, isSelecting: boolean) => {
    setItemSelected(item, isSelecting);
  };

  return (
    <PageSection>
      <Toolbar>
        <ToolbarContent>
          {props.showCheckbox ? (
            <DropdownCheckbox
              selectedItems={props.selectedTeams}
              deSelectAll={props.setSelectedTeams}
              allItemsList={props.items}
              itemsPerPageList={paginatedItems}
              onItemSelect={onSelectItem}
            />
          ) : null}
          {props.filterWithDropdown ? (
            <FilterWithDropdown
              searchState={search}
              onChange={setSearch}
              dropdownItems={props.dropdownItems}
              searchInputText={searchInputText}
            />
          ) : (
            <FilterInput searchState={search} onChange={setSearch} />
          )}
          {props.showCheckbox ? (
            <ToolbarItem>
              <ToggleGroup aria-label="Default with single selectable">
                <ToggleGroupItem
                  text="All"
                  buttonId="All"
                  isSelected={tableMode === 'All'}
                  onChange={onTableModeChange}
                />
                <ToggleGroupItem
                  text="Selected"
                  buttonId="Selected"
                  isSelected={tableMode === 'Selected'}
                  onChange={onTableModeChange}
                />
              </ToggleGroup>
            </ToolbarItem>
          ) : null}
          <ToolbarPagination
            itemsList={filteredItems}
            perPage={perPage}
            page={page}
            setPage={setPage}
            setPerPage={setPerPage}
            total={filteredItems.length}
          />
        </ToolbarContent>
      </Toolbar>
      <TableComposable aria-label="Selectable table">
        <Thead>
          <Tr>
            {props.showCheckbox ? <Th /> : null}
            <Th>{ColumnNames.name}</Th>
            <Th>{ColumnNames.role}</Th>
            <Th>{ColumnNames.members}</Th>
            <Th>{ColumnNames.lastUpdated}</Th>
          </Tr>
        </Thead>
        {paginatedItems.map((team, rowIndex) => {
          return (
            <Tbody key={team.name}>
              <Tr>
                {props.showCheckbox ? (
                  <Td
                    select={{
                      rowIndex,
                      onSelect: (_event, isSelecting) =>
                        onSelectItem(team, rowIndex, isSelecting),
                      isSelected: isItemSelected(team),
                    }}
                  />
                ) : null}
                <Td dataLabel={ColumnNames.name}>{team.name}</Td>
                <Td dataLabel={ColumnNames.role}>{team.role}</Td>
                <Td dataLabel={ColumnNames.members}>
                  {team.member_count > 1
                    ? team.member_count + ' Members'
                    : team.member_count + ' Member'}
                </Td>
                <Td dataLabel={ColumnNames.lastUpdated}>
                  {team.last_updated ? formatDate(team.last_updated) : 'Never'}
                </Td>
              </Tr>
            </Tbody>
          );
        })}
      </TableComposable>
      <PanelFooter>
        <ToolbarPagination
          itemsList={filteredItems}
          perPage={perPage}
          page={page}
          setPage={setPage}
          setPerPage={setPerPage}
          bottom={true}
          total={filteredItems.length}
        />
      </PanelFooter>
    </PageSection>
  );
}

interface TeamViewProps {
  items: any[];
  selectedTeams?: any[];
  setSelectedTeams?: (teams) => void;
  dropdownItems?: any[];
  showCheckbox: boolean;
  showToggleGroup: boolean;
  searchInputText?: string;
  filterWithDropdown: boolean;
}
