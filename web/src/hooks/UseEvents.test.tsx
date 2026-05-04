import {renderHook} from '@testing-library/react';
import {useEvents} from './UseEvents';

vi.mock('./UseQuayConfig', () => ({
  useQuayConfig: vi.fn(() => ({
    features: {
      SECURITY_SCANNER: true,
      BUILD_SUPPORT: true,
      REPO_MIRROR: true,
      IMAGE_EXPIRY_TRIGGER: true,
    },
  })),
}));

describe('UseEvents', () => {
  it('returns all 11 notification events', () => {
    const {result} = renderHook(() => useEvents());
    expect(result.current.events).toHaveLength(11);
  });

  it('includes repoPush event that is always enabled', () => {
    const {result} = renderHook(() => useEvents());
    const pushEvent = result.current.events.find((e) => e.type === 'repo_push');
    expect(pushEvent).toBeDefined();
    expect(pushEvent.title).toBe('Push to Repository');
    expect(pushEvent.enabled).toBe(true);
  });

  it('enables security scanner events when feature is on', () => {
    const {result} = renderHook(() => useEvents());
    const vulnEvent = result.current.events.find(
      (e) => e.type === 'vulnerability_found',
    );
    expect(vulnEvent).toBeDefined();
    expect(vulnEvent.enabled).toBe(true);
  });

  it('enables build events when BUILD_SUPPORT is on', () => {
    const {result} = renderHook(() => useEvents());
    const buildEvents = result.current.events.filter((e) =>
      e.type.startsWith('build_'),
    );
    expect(buildEvents.length).toBeGreaterThanOrEqual(4);
    buildEvents.forEach((e) => expect(e.enabled).toBe(true));
  });

  it('enables mirror events when REPO_MIRROR is on', () => {
    const {result} = renderHook(() => useEvents());
    const mirrorEvents = result.current.events.filter((e) =>
      e.title.toLowerCase().includes('mirror'),
    );
    expect(mirrorEvents.length).toBeGreaterThanOrEqual(3);
    mirrorEvents.forEach((e) => expect(e.enabled).toBe(true));
  });
});
