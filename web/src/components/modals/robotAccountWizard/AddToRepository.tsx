import {useRecoilState} from 'recoil';
import {searchRepoState} from 'src/atoms/RepositoryState';
import React, {useEffect, useState} from 'react';
import {
  PageSection,
  PanelFooter,
  Text,
  TextContent,
  TextVariants,
  ToggleGroup,
  ToggleGroupItem,
  ToggleGroupItemProps,
  Toolbar,
  ToolbarContent,
  ToolbarItem,
  Dropdown,
  DropdownItem,
  DropdownSeparator,
  KebabToggle,
} from '@patternfly/react-core';
import {DropdownCheckbox} from 'src/components/toolbar/DropdownCheckbox';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';
import {
  TableComposable,
  Tbody,
  Td,
  Th,
  Thead,
  Tr,
} from '@patternfly/react-table';
import {DropdownWithDescription} from 'src/components/toolbar/DropdownWithDescription';
import {IRepository} from 'src/resources/RepositoryResource';
import {formatDate} from 'src/libs/utils';
import _ from 'lodash';
import {SearchInput} from 'src/components/toolbar/SearchInput';

const ColumnNames = {
  name: 'Repository',
  permissions: 'Permissions',
  lastUpdated: 'Last Updated',
};

type TableModeType = 'All' | 'Selected';

const defaultSelectedVal = 'Read';
const defaultUnSelectedVal = 'None';

export default function AddToRepository(props: AddToRepositoryProps) {
  const [tableMode, setTableMode] = useState<TableModeType>('All');
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(10);
  const [tableItems, setTableItems] = useState([]);
  const [search, setSearch] = useRecoilState(searchRepoState);
  const [robotRepoPermsMapping, setRobotRepoPermsMapping] = useState({});
  const [isUserEntry, setUserEntry] = useState(false);
  const [updatedRepoPerms, setUpdatedRepoPerms] = useState({});
  const [isKebabOpen, setKebabOpen] = useState(false);

  props.repos.sort((r1, r2) => {
    return r1.last_modified > r2.last_modified ? -1 : 1;
  });

  const onTableModeChange: ToggleGroupItemProps['onChange'] = (
    _isSelected,
    event,
  ) => {
    const id = event.currentTarget.id;
    setTableMode(id as TableModeType);
    if (id == 'All') {
      setTableItems(props.repos);
    } else if (id == 'Selected') {
      const selectedItems = [];
      props.repos.map(function (repo) {
        if (props.selectedRepos.includes(repo.name)) {
          selectedItems.push(repo);
        }
      });
      setTableItems(selectedItems);
    }
  };

  const setItemSelected = (item, isSelecting = true) => {
    props.setSelectedRepos((prevSelected) => {
      const otherSelectedItems = prevSelected.filter((r) => r !== item.name);
      return isSelecting
        ? [...otherSelectedItems, item.name]
        : otherSelectedItems;
    });
  };

  const isItemSelected = (item) => props.selectedRepos.includes(item.name);

  const onSelectItem = (item, rowIndex: number, isSelecting: boolean) => {
    setItemSelected(item, isSelecting);
  };

  useEffect(() => {
    if (tableMode == 'All') {
      setTableItems(props.repos);
    }
    updateTable();
  }, [props.robotPermissions]);

  const updateTable = () => {
    if (!props.robotPermissions) {
      return;
    }
    const temp = {};
    props.robotPermissions?.map(function (repoPerm) {
      const repo = repoPerm.repository.name;
      const permission =
        repoPerm.role.charAt(0).toUpperCase() + repoPerm.role.slice(1);
      const newItems = {
        ...temp,
        [repo]: permission,
      };
      setItemSelected({name: repo}, true);
      setRobotRepoPermsMapping(newItems);
      setUpdatedRepoPerms(Object.assign({}, newItems));
      temp[repo] = permission;
    });
  };

  const filteredItems =
    search.query !== ''
      ? tableItems.filter((item) => {
          const Itemname = item.name;
          return Itemname.includes(search.query);
        })
      : tableItems;

  const paginatedItems = filteredItems?.slice(
    page * perPage - perPage,
    page * perPage - perPage + perPage,
  );

  const updateRepoPerms = (permission, repo) => {
    const repoName = repo.name ? repo.name : repo;
    if (props.wizardStep) {
      props.setSelectedRepoPerms((prevSelected) =>
        prevSelected.filter((item) => item.name !== repoName),
      );

      if (permission == 'None') {
        return;
      }

      props.setSelectedRepoPerms((prevSelected) => {
        const newPerms = {
          name: repoName,
          permission: permission,
          last_modified: repo?.last_modified,
        };
        return [...prevSelected, newPerms];
      });
    } else {
      const tempItem = updatedRepoPerms;
      delete tempItem[repoName];
      setUpdatedRepoPerms(tempItem);
      if (permission == 'None') {
        return;
      }
      tempItem[repoName] = permission;
      setUpdatedRepoPerms(tempItem);
      updateRobotAccountsList();
    }
  };

  const fetchRepoPermission = (repo) => {
    if (!props.wizardStep && updatedRepoPerms[repo.name] != null) {
      return updatedRepoPerms[repo.name];
    }

    for (const repoPerm of props.selectedRepoPerms) {
      if (repoPerm.name == repo.name) {
        return repoPerm.permission;
      }
    }
    return 'None';
  };

  const dropdownOnSelect = (selectedVal) => {
    setUserEntry(true);
    props.selectedRepos.map((repo) => {
      // set row as selected/un-selected
      updateRepoPerms(selectedVal.name, repo);
    });
  };

  const onKebabToggle = (isKebabOpen: boolean) => {
    setKebabOpen(isKebabOpen);
  };

  const onKebabSelect = () => {
    const element = document.getElementById('toggle-bulk-perms-kebab');
    setKebabOpen(false);
    element.focus();
  };

  const kebabItems = props.dropdownItems.map((item) => (
    <DropdownItem
      key={item.name}
      description={item.description}
      onClick={() => dropdownOnSelect(item)}
    >
      {item.name}
    </DropdownItem>
  ));

  const updateRobotAccountsList = () => {
    if (
      !props.wizardStep &&
      !_.isEqual(updatedRepoPerms, robotRepoPermsMapping)
    ) {
      setTimeout(() => props.setShowRepoModalSave(true), 0);
      setTimeout(() => props.setPrevRepoPerms(robotRepoPermsMapping), 0);
      setTimeout(() => props.setNewRepoPerms(updatedRepoPerms), 0);
    }

    if (
      !props.wizardStep &&
      _.isEqual(updatedRepoPerms, robotRepoPermsMapping)
    ) {
      setTimeout(() => props.setShowRepoModalSave(false), 0);
    }
  };

  updateRobotAccountsList();

  return (
    <>
      <TextContent>
        <Text component={TextVariants.h1}>Add to repository (optional)</Text>
      </TextContent>
      <PageSection>
        <Toolbar>
          <ToolbarContent>
            <DropdownCheckbox
              selectedItems={props.selectedRepos}
              deSelectAll={props.setSelectedRepos}
              allItemsList={props.repos}
              itemsPerPageList={paginatedItems}
              onItemSelect={onSelectItem}
              id="add-repository-bulk-select"
            />
            <SearchInput
              searchState={search}
              onChange={setSearch}
              id="robot-wizard-repo-search"
            />
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
            <ToolbarItem>
              <Dropdown
                onSelect={onKebabSelect}
                toggle={
                  <KebabToggle
                    id="toggle-bulk-perms-kebab"
                    onToggle={onKebabToggle}
                  />
                }
                isOpen={isKebabOpen}
                isPlain
                dropdownItems={kebabItems}
              />
            </ToolbarItem>
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
              <Th />
              <Th>{ColumnNames.name}</Th>
              <Th>{ColumnNames.permissions}</Th>
              <Th>{ColumnNames.lastUpdated}</Th>
            </Tr>
          </Thead>
          {paginatedItems.map((repo, rowIndex) => {
            return (
              <Tbody key={rowIndex}>
                <Tr>
                  <Td
                    select={{
                      rowIndex,
                      onSelect: (_event, isSelecting) =>
                        onSelectItem(repo, rowIndex, isSelecting),
                      isSelected: isItemSelected(repo),
                    }}
                  />
                  <Td dataLabel={ColumnNames.name}>{repo.name}</Td>
                  <Td dataLabel={ColumnNames.permissions}>
                    <DropdownWithDescription
                      dropdownItems={props.dropdownItems}
                      selectedVal={fetchRepoPermission(repo)}
                      onSelect={updateRepoPerms}
                      repo={repo}
                      isItemSelected={isItemSelected(repo)}
                      OnRowSelect={onSelectItem}
                      rowIndex={rowIndex}
                      setUserEntry={setUserEntry}
                      isUserEntry={isUserEntry}
                      wizarStep={false}
                    />
                  </Td>
                  <Td dataLabel={ColumnNames.lastUpdated}>
                    {repo.last_modified
                      ? formatDate(repo.last_modified)
                      : 'Never'}
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
    </>
  );
}

interface AddToRepositoryProps {
  namespace: string;
  dropdownItems: any[];
  selectedRepos?: any[];
  repos: IRepository[];
  setSelectedRepos: (repos) => void;
  selectedRepoPerms: any[];
  setSelectedRepoPerms: (repoPerm) => void;
  robotPermissions?: any[];
  wizardStep: boolean;
  robotName?: string;
  fetchingRobotPerms?: boolean;
  setPrevRepoPerms?: (preVal) => void;
  setNewRepoPerms?: (newVal) => void;
  setShowRepoModalSave?: (boolean) => void;
}
