import {render, screen, userEvent, waitFor} from 'src/test-utils';
import {
  NotificationEventType,
  NotificationMethodType,
} from 'src/resources/NotificationResource';
import type {NotificationFilter} from 'src/hooks/UseNotifications';
import type {RepoNotification} from 'src/resources/NotificationResource';
import Notifications from './Notifications';

const mockUseNotifications = vi.hoisted(() => vi.fn());
const mockDeleteNotifications = vi.hoisted(() => vi.fn());

vi.mock('src/hooks/UseNotifications', () => ({
  useNotifications: mockUseNotifications,
}));

vi.mock('src/hooks/UseEvents', () => ({
  useEvents: () => ({
    events: [
      {
        type: NotificationEventType.repoPush,
        title: 'Push to Repository',
        icon: null,
      },
    ],
  }),
}));

vi.mock('src/hooks/UseNotificationMethods', () => ({
  useNotificationMethods: () => ({
    notificationMethods: [
      {type: NotificationMethodType.webhook, title: 'Webhook POST'},
    ],
  }),
}));

vi.mock('src/components/toolbar/DropdownCheckbox', () => ({
  DropdownCheckbox: (props: DropdownCheckboxProps) => (
    <>
      <button
        onClick={() => props.onItemSelect(props.itemsPerPageList[0], 0, true)}
        type="button"
      >
        Select first notification
      </button>
      <output data-testid="selected-notification-uuids">
        {props.selectedItems.map((notification) => notification.uuid).join(',')}
      </output>
    </>
  ),
}));

vi.mock('src/components/toolbar/ToolbarPagination', () => ({
  ToolbarPagination: (props: ToolbarPaginationProps) => (
    <button onClick={() => props.setPage(2)} type="button">
      Go to page two
    </button>
  ),
}));

vi.mock('./NotificationsActions', () => ({
  default: (props: NotificationsActionsProps) => (
    <button
      disabled={props.isDisabled}
      onClick={() =>
        mockDeleteNotifications(
          props.selectedItems.map((notification) => notification.uuid),
        )
      }
      type="button"
    >
      Delete selected notifications
    </button>
  ),
}));

type DropdownCheckboxProps = {
  itemsPerPageList: RepoNotification[];
  onItemSelect: (
    notification: RepoNotification,
    rowIndex: number,
    isSelecting: boolean,
  ) => void;
  selectedItems: RepoNotification[];
};

type ToolbarPaginationProps = {
  setPage: (page: number) => void;
};

type NotificationsActionsProps = {
  isDisabled: boolean;
  selectedItems: RepoNotification[];
};

vi.mock('./NotificationsFilter', () => ({
  default: () => null,
}));

vi.mock('./NotificationsFilterChips', () => ({
  default: () => null,
}));

vi.mock('./NotificationsKebab', () => ({
  default: () => null,
}));

const notifications = Array.from({length: 21}, (_, index) => ({
  config: {},
  event: NotificationEventType.repoPush,
  event_config: {},
  method: NotificationMethodType.webhook,
  title: `Notification ${index + 1}`,
  uuid: `notification-${index + 1}`,
}));

describe('Notifications', () => {
  let filteredNotifications = notifications;
  let filter: NotificationFilter = {event: [], status: []};

  beforeEach(() => {
    vi.clearAllMocks();
    filteredNotifications = notifications;
    filter = {event: [], status: []};
    mockUseNotifications.mockImplementation(() => ({
      notifications,
      filteredNotifications,
      loading: false,
      error: false,
      filter,
      setFilter: vi.fn(),
      resetFilter: vi.fn(),
    }));
  });

  it('keeps selections across pages and excludes hidden selections from delete actions', async () => {
    const user = userEvent.setup();
    const {rerender} = render(
      <Notifications org="myorg" repo="myrepo" setDrawerContent={vi.fn()} />,
    );

    await user.click(
      screen.getByRole('button', {name: 'Select first notification'}),
    );
    await user.click(screen.getByRole('button', {name: 'Go to page two'}));
    await user.click(
      screen.getByRole('button', {name: 'Select first notification'}),
    );

    expect(screen.getByTestId('selected-notification-uuids')).toHaveTextContent(
      'notification-1,notification-21',
    );

    filter = {event: [NotificationEventType.repoPush], status: []};
    filteredNotifications = [notifications[0]];
    rerender(
      <Notifications org="myorg" repo="myrepo" setDrawerContent={vi.fn()} />,
    );

    await waitFor(() => {
      expect(
        screen.getByTestId('selected-notification-uuids'),
      ).toHaveTextContent('notification-1');
    });

    await user.click(
      screen.getByRole('button', {name: 'Delete selected notifications'}),
    );
    expect(mockDeleteNotifications).toHaveBeenCalledWith(['notification-1']);
  });
});
