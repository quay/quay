import {render, screen, userEvent} from 'src/test-utils';
import {NotificationEventType} from 'src/resources/NotificationResource';
import type {NotificationFilter} from 'src/hooks/UseNotifications';
import NotificationsFilter from './NotificationsFilter';

const mockUseEvents = vi.hoisted(() => vi.fn());

vi.mock('src/hooks/UseEvents', () => ({
  useEvents: mockUseEvents,
}));

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
});
