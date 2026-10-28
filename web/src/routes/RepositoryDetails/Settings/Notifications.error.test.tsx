import {render, screen, waitFor} from 'src/test-utils';
import * as NotificationResource from 'src/resources/NotificationResource';
import Notifications from './Notifications';

describe('Notifications loading errors', () => {
  it('renders the error state when the initial notification fetch fails', async () => {
    vi.spyOn(NotificationResource, 'fetchNotifications').mockRejectedValueOnce(
      new Error('notifications unavailable'),
    );

    render(
      <Notifications org="myorg" repo="myrepo" setDrawerContent={vi.fn()} />,
    );

    await waitFor(() => {
      expect(screen.getByText('Unable to load notifications')).toBeVisible();
    });
  });
});
