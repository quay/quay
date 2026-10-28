import {render, screen, userEvent} from 'src/test-utils';
import {Table, Th, Thead, Tr} from '@patternfly/react-table';
import {useState} from 'react';
import {NotificationEventType} from 'src/resources/NotificationResource';
import {
  NotifiationStatus,
  type NotificationFilter,
} from 'src/hooks/UseNotifications';
import {usePaginatedSortableTable} from 'src/hooks/usePaginatedSortableTable';
import {DrawerContentType} from '../Types';
import NotificationsFilter from './NotificationsFilter';
import NotificationsToolbar from './NotificationsToolbar';

const mockUseEvents = vi.hoisted(() => vi.fn());

vi.mock('src/hooks/UseEvents', () => ({
  useEvents: mockUseEvents,
}));

function NotificationsFilterWithSortableStatusHeader() {
  const [filter, setFilter] = useState<NotificationFilter>({
    event: [],
    status: [],
  });
  const {getSortableSort} = usePaginatedSortableTable([{status: 'Enabled'}], {
    columns: {0: (notification) => notification.status},
  });

  return (
    <>
      <NotificationsFilter
        filter={filter}
        setFilter={(updateFilter) => setFilter(updateFilter)}
      />
      <Table aria-label="Notifications">
        <Thead>
          <Tr>
            <Th sort={getSortableSort(0)}>Status</Th>
          </Tr>
        </Thead>
      </Table>
    </>
  );
}

function NotificationsToolbarWithActiveStatusFilter() {
  const [filter, setFilter] = useState<NotificationFilter>({
    event: [],
    status: [NotifiationStatus.disabled],
  });

  return (
    <NotificationsToolbar
      allItems={[]}
      deselectAll={() => undefined}
      filter={filter}
      onItemSelect={() => undefined}
      org="test-org"
      page={1}
      paginatedItems={[]}
      perPage={20}
      repo="test-repo"
      resetFilter={(field) =>
        setFilter((previous) =>
          field ? {...previous, [field]: []} : {event: [], status: []},
        )
      }
      selectedItems={[]}
      setDrawerContent={(_content: DrawerContentType) => undefined}
      setFilter={(updateFilter) => setFilter(updateFilter)}
      setPage={() => undefined}
      setPerPage={() => undefined}
    />
  );
}

describe('NotificationsFilter', () => {
  beforeEach(() => {
    mockUseEvents.mockReturnValue({
      events: [
        {
          type: NotificationEventType.repoPush,
          title: 'Push to Repository',
          icon: null,
        },
      ],
    });
  });

  it('opens the events flyout from its button and selects an event', async () => {
    const user = userEvent.setup();
    const setFilter = vi.fn();

    render(
      <NotificationsFilter
        filter={{event: [], status: []}}
        setFilter={setFilter}
      />,
    );

    await user.click(screen.getByRole('button', {name: 'Filter'}));
    const eventsButton = screen.getByRole('button', {name: 'Events'});
    await user.hover(eventsButton);
    await user.click(
      screen.getByRole('checkbox', {name: 'Push to Repository'}),
    );

    const updateFilter = setFilter.mock.calls[0][0] as (
      previous: NotificationFilter,
    ) => NotificationFilter;
    expect(updateFilter({event: [], status: []})).toEqual({
      event: [NotificationEventType.repoPush],
      status: [],
    });
  });

  it('scopes the status filter flyout when a sortable status header exists', async () => {
    const user = userEvent.setup();

    render(<NotificationsFilterWithSortableStatusHeader />);

    await user.click(screen.getByRole('button', {name: 'Filter'}));
    expect(screen.getAllByRole('button', {name: 'Status'})).toHaveLength(2);

    await user.hover(screen.getByTestId('notifications-filter-status'));
    const disabled = screen.getByRole('checkbox', {name: 'Disabled'});
    await user.click(disabled);
    expect(disabled).toBeChecked();

    await user.click(disabled);
    expect(disabled).not.toBeChecked();
  });

  it('keeps the Filter toggle uniquely addressable when the toolbar can clear active filters', () => {
    render(<NotificationsToolbarWithActiveStatusFilter />);

    expect(screen.getAllByRole('button', {name: /filter/i})).toHaveLength(2);
    expect(
      screen.getByRole('button', {name: 'Filter', exact: true}),
    ).toBeVisible();
    expect(
      screen.getByRole('button', {name: 'Clear all filters', exact: true}),
    ).toBeVisible();
  });
});
