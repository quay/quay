import {render, screen, userEvent} from 'src/test-utils';
import {NotificationDrawerListComponent} from './NotificationDrawerList';

const mockUseCurrentUser = vi.hoisted(() =>
  vi.fn(() => ({user: {username: 'testuser'}})),
);

const mockUseAppNotifications = vi.hoisted(() =>
  vi.fn(() => ({
    notifications: [],
    dismissNotification: vi.fn(),
    loading: false,
    refetch: vi.fn(),
  })),
);

const mockNavigate = vi.hoisted(() => vi.fn());

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {...actual, useNavigate: () => mockNavigate};
});

vi.mock('src/hooks/UseCurrentUser', () => ({
  useCurrentUser: mockUseCurrentUser,
}));

vi.mock('src/hooks/useAppNotifications', () => ({
  useAppNotifications: mockUseAppNotifications,
}));

describe('NotificationDrawerListComponent', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('passes true to useAppNotifications for authenticated users', () => {
    mockUseCurrentUser.mockReturnValue({user: {username: 'testuser'}});

    render(<NotificationDrawerListComponent />);
    expect(mockUseAppNotifications).toHaveBeenCalledWith(true);
  });

  it('passes false to useAppNotifications for anonymous users', () => {
    mockUseCurrentUser.mockReturnValue({
      user: {username: '', anonymous: true},
    });

    render(<NotificationDrawerListComponent />);
    expect(mockUseAppNotifications).toHaveBeenCalledWith(false);
  });

  describe('clicking a notification', () => {
    const renderWith = (notification) => {
      mockUseCurrentUser.mockReturnValue({user: {username: 'testuser'}});
      mockUseAppNotifications.mockReturnValue({
        notifications: [
          {id: 'n1', level: 'info', created: '', ...notification},
        ],
        dismissNotification: vi.fn(),
        loading: false,
        refetch: vi.fn(),
      });
      const onNavigate = vi.fn();
      render(<NotificationDrawerListComponent onNavigate={onNavigate} />);
      return onNavigate;
    };

    beforeEach(() => {
      mockNavigate.mockClear();
    });

    it('opens the repository and calls onNavigate', async () => {
      const onNavigate = renderWith({
        kind: 'repo_push',
        metadata: {repository: 'testuser/notif-repo'},
      });

      await userEvent.click(screen.getByText(/notif-repo/));

      expect(mockNavigate).toHaveBeenCalledWith(
        '/repository/testuser/notif-repo',
      );
      expect(onNavigate).toHaveBeenCalledTimes(1);
      expect(localStorage.getItem('notification-read-status')).toBe('["n1"]');
    });

    it('only marks a notification without a link as read', async () => {
      const onNavigate = renderWith({
        kind: 'password_required',
        metadata: {},
      });

      await userEvent.click(screen.getByText(/a password must be set/));

      expect(mockNavigate).not.toHaveBeenCalled();
      expect(onNavigate).not.toHaveBeenCalled();
      expect(localStorage.getItem('notification-read-status')).toBe('["n1"]');
    });
  });
});
