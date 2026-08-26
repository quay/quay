import {renderHook} from '@testing-library/react';
import {useNotificationMethods} from './UseNotificationMethods';
import {useQuayConfig} from './UseQuayConfig';
import {NotificationMethodType} from 'src/resources/NotificationResource';

vi.mock('./UseQuayConfig', () => ({
  useQuayConfig: vi.fn(),
}));

describe('useNotificationMethods', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns all notification methods with MAILING enabled', () => {
    vi.mocked(useQuayConfig).mockReturnValue({
      features: {MAILING: true},
      config: {REGISTRY_TITLE_SHORT: 'Quay'},
    } as any);
    const {result} = renderHook(() => useNotificationMethods());
    const {notificationMethods} = result.current;
    expect(notificationMethods).toHaveLength(6);
    const emailMethod = notificationMethods.find(
      (m) => m.type === NotificationMethodType.email,
    );
    expect(emailMethod?.enabled).toBe(true);
  });

  it('disables email method when MAILING is false', () => {
    vi.mocked(useQuayConfig).mockReturnValue({
      features: {MAILING: false},
      config: {REGISTRY_TITLE_SHORT: 'Quay'},
    } as any);
    const {result} = renderHook(() => useNotificationMethods());
    const emailMethod = result.current.notificationMethods.find(
      (m) => m.type === NotificationMethodType.email,
    );
    expect(emailMethod?.enabled).toBe(false);
  });

  it('uses REGISTRY_TITLE_SHORT for quay notification title', () => {
    vi.mocked(useQuayConfig).mockReturnValue({
      features: {MAILING: true},
      config: {REGISTRY_TITLE_SHORT: 'MyReg'},
    } as any);
    const {result} = renderHook(() => useNotificationMethods());
    const quayMethod = result.current.notificationMethods.find(
      (m) => m.type === NotificationMethodType.quaynotification,
    );
    expect(quayMethod?.title).toBe('MyReg Notification');
  });
});
