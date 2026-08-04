import {render} from 'src/test-utils';
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
});
