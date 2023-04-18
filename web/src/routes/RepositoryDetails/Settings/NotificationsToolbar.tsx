import {
  Button,
  Toolbar,
  ToolbarContent,
  ToolbarGroup,
  ToolbarItem,
} from '@patternfly/react-core';
import {DropdownCheckbox} from 'src/components/toolbar/DropdownCheckbox';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';
import {DrawerContentType} from '../Types';
import {RepoNotification} from 'src/resources/NotificationResource';
import NotificationsFilter from './NotificationsFilter';
import {NotificationFilter} from 'src/hooks/UseNotifications';
import NotificationsFilterChips from './NotificationsFilterChips';
import Actions from './NotificationsActions';

export default function NotificationsToolbar(props: NotificationsToolbarProps) {
  return (
    <Toolbar clearAllFilters={() => props.resetFilter()}>
      <ToolbarContent>
        <DropdownCheckbox
          id="notifications-select-all"
          selectedItems={props.selectedItems}
          deSelectAll={props.deselectAll}
          allItemsList={props.allItems}
          itemsPerPageList={props.paginatedItems}
          onItemSelect={props.onItemSelect}
        />
        <ToolbarItem>
          <NotificationsFilter
            filter={props.filter}
            setFilter={props.setFilter}
          />
        </ToolbarItem>
        <ToolbarGroup variant="filter-group">
          <NotificationsFilterChips
            filter={props.filter}
            setFilter={props.setFilter}
            resetFilter={props.resetFilter}
          />
        </ToolbarGroup>
        <ToolbarItem>
          <Button
            onClick={() =>
              props.setDrawerContent(DrawerContentType.CreateNotification)
            }
          >
            Create Notification
          </Button>
        </ToolbarItem>
        <ToolbarItem>
          <Actions
            isDisabled={props.selectedItems.length == 0}
            org={props.org}
            repo={props.repo}
            selectedItems={props.selectedItems}
            deselectAll={props.deselectAll}
          />
        </ToolbarItem>
        <ToolbarPagination
          itemsList={props.allItems}
          perPage={props.perPage}
          page={props.page}
          setPage={props.setPage}
          setPerPage={props.setPerPage}
        />
      </ToolbarContent>
    </Toolbar>
  );
}

interface NotificationsToolbarProps {
  org: string;
  repo: string;

  allItems: RepoNotification[];
  paginatedItems: RepoNotification[];
  selectedItems: RepoNotification[];

  page: number;
  setPage: (page: number) => void;
  perPage: number;
  setPerPage: (perPage: number) => void;

  filter: NotificationFilter;
  setFilter(
    set: (prev: NotificationFilter) => NotificationFilter | NotificationFilter,
  ): void;
  resetFilter(field?: string): void;

  onItemSelect: (
    item: RepoNotification,
    rowIndex: number,
    isSelecting: boolean,
  ) => void;
  deselectAll: () => void;
  setDrawerContent: (content: DrawerContentType) => void;
}
