import {renderHook} from '@testing-library/react';
import {useAnalytics} from './UseAnalytics';
import {useQuayConfig} from './UseQuayConfig';

vi.mock('./UseQuayConfig', () => ({
  useQuayConfig: vi.fn(),
}));

describe('UseAnalytics', () => {
  const originalHead = document.head.innerHTML;
  const originalBody = document.body.innerHTML;

  afterEach(() => {
    document.head.innerHTML = originalHead;
    document.body.innerHTML = originalBody;
  });

  it('does not inject scripts when hostname is not quay.io', () => {
    vi.mocked(useQuayConfig).mockReturnValue({
      config: {SERVER_HOSTNAME: 'registry.example.com'},
    } as any);
    renderHook(() => useAnalytics());
    const scripts = document.head.querySelectorAll('script');
    expect(scripts.length).toBe(0);
  });

  it('injects analytics scripts for quay.io', () => {
    vi.mocked(useQuayConfig).mockReturnValue({
      config: {SERVER_HOSTNAME: 'quay.io'},
    } as any);
    renderHook(() => useAnalytics());
    const scripts = document.head.querySelectorAll('script');
    expect(scripts.length).toBeGreaterThanOrEqual(2);
    const srcs = Array.from(scripts).map((s) => s.getAttribute('src'));
    expect(srcs).toContain('https://www.redhat.com/ma/dpal.js');
    expect(srcs).toContain(
      'https://static.redhat.com/libs/redhat/marketing/latest/trustarc/trustarc.js',
    );
  });

  it('injects staging scripts for stage.quay.io', () => {
    vi.mocked(useQuayConfig).mockReturnValue({
      config: {SERVER_HOSTNAME: 'stage.quay.io'},
    } as any);
    renderHook(() => useAnalytics());
    const scripts = document.head.querySelectorAll('script');
    const srcs = Array.from(scripts).map((s) => s.getAttribute('src'));
    expect(srcs).toContain('https://www.redhat.com/ma/dpal-staging.js');
    expect(srcs).toContain(
      'https://static.redhat.com/libs/redhat/marketing/latest/trustarc/trustarc.stage.js',
    );
  });

  it('does not inject scripts when config is null', () => {
    vi.mocked(useQuayConfig).mockReturnValue(null);
    renderHook(() => useAnalytics());
    const scripts = document.head.querySelectorAll('script');
    expect(scripts.length).toBe(0);
  });
});
