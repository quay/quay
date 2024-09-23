import {
  Button,
  Flex,
  FlexItem,
  Icon,
  PanelFooter,
  Toolbar,
  ToolbarContent,
  ToolbarItem,
} from '@patternfly/react-core';
import Conditional from 'src/components/empty/Conditional';
import {DropdownCheckbox} from 'src/components/toolbar/DropdownCheckbox';
import {SearchDropdown} from 'src/components/toolbar/SearchDropdown';
import {SearchInput} from 'src/components/toolbar/SearchInput';
import {SearchState} from 'src/components/toolbar/SearchTypes';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';
import {TrashIcon} from '@patternfly/react-icons';
import {OrganizationDrawerContentType} from 'src/routes/OrganizationsList/Organization/Organization';
import {IOAuthApplication} from 'src/hooks/UseOAuthApplications';

export default function OAuthApplicationsToolbar(
  props: OAuthApplicationsToolbarProps,
) {
  return (
    <>
      <Toolbar>
        <ToolbarContent>
          <DropdownCheckbox
            selectedItems={props.selectedItems}
            deSelectAll={props.deSelectAll}
            allItemsList={props.allItems}
            itemsPerPageList={props.paginatedItems}
            onItemSelect={props.onItemSelect}
            id="default-perm-bulk-select"
          />
          <SearchDropdown
            items={props.searchOptions}
            searchState={props.search}
            setSearchState={props.setSearch}
          />
          <Flex className="pf-v5-u-mr-md">
            <FlexItem>
              <SearchInput
                searchState={props.search}
                onChange={props.setSearch}
                id="default-permissions-search"
              />
            </FlexItem>
          </Flex>
          <Button
            onClick={() =>
              props.setDrawerContent(
                OrganizationDrawerContentType.CreateOAuthApplicationDrawer,
              )
            }
            data-testid="create-default-permissions-btn"
          >
            Create OAuth Application
          </Button>
          <Conditional if={props.selectedItems?.length !== 0}>
            <ToolbarItem>
              <Button
                style={{paddingBottom: '0px'}}
                icon={
                  <Icon size="lg">
                    <TrashIcon />
                  </Icon>
                }
                variant="plain"
                onClick={props.handleBulkDeleteModalToggle}
                data-testid="default-perm-bulk-delete-icon"
              />
            </ToolbarItem>
          </Conditional>
          <ToolbarPagination
            itemsList={props.allItems}
            perPage={props.perPage}
            page={props.page}
            setPage={props.setPage}
            setPerPage={props.setPerPage}
          />
        </ToolbarContent>
      </Toolbar>
      {props.children}
      <PanelFooter>
        <ToolbarPagination
          itemsList={props.allItems}
          perPage={props.perPage}
          page={props.page}
          setPage={props.setPage}
          setPerPage={props.setPerPage}
          bottom={true}
        />
      </PanelFooter>
    </>
  );
}

interface OAuthApplicationsToolbarProps {
  selectedItems: IOAuthApplication[];
  deSelectAll: () => void;
  allItems: IOAuthApplication[];
  paginatedItems: IOAuthApplication[];
  onItemSelect: (
    item: IOAuthApplication,
    rowIndex: number,
    isSelecting: boolean,
  ) => void;
  page: number;
  setPage: (page: number) => void;
  perPage: number;
  setPerPage: (perPage: number) => void;
  searchOptions: string[];
  search: SearchState;
  setSearch: (search: SearchState) => void;
  setDrawerContent: (content: OrganizationDrawerContentType) => void;
  children?: React.ReactNode;
  handleBulkDeleteModalToggle: () => void;
}
