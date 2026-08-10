import {renderHook} from '@testing-library/react';
import {useServiceStatus} from './UseServiceStatus';

vi.mock('src/libs/utils', () => ({
  isNullOrUndefined: vi.fn((v) => v === null || v === undefined),
}));

vi.mock('./UseExternalScripts', () => ({
  useExternalScripts: vi.fn(() => ({statusPageLoaded: true})),
}));

function mockStatusPage(summaryData: any) {
  (window as any).StatusPage = {
    page: function () {
      this.summary = ({success}: {success: (data: any) => void}) => {
        success(summaryData);
      };
    },
  };
}

describe('UseServiceStatus', () => {
  afterEach(() => {
    delete (window as any).StatusPage;
  });

  it('returns null statusData when StatusPage is not loaded', () => {
    const {result} = renderHook(() => useServiceStatus());
    expect(result.current.statusData).toBeNull();
  });

  it('parses StatusPage data and extracts quay component info', () => {
    mockStatusPage({
      components: [
        {
          id: 'cllr1k2dzsf7',
          name: 'Quay.io',
          status: 'operational',
          components: ['sub1', 'sub2'],
        },
        {id: 'sub1', name: 'API', status: 'operational'},
        {id: 'sub2', name: 'Registry', status: 'degraded_performance'},
      ],
      incidents: [{id: 'inc1', components: [{id: 'sub1'}]}],
      scheduled_maintenances: [],
    });

    const {result} = renderHook(() => useServiceStatus());
    expect(result.current.statusData).not.toBeNull();
    expect(result.current.statusData.indicator).toBe('none');
    expect(result.current.statusData.description).toBe(
      'All Systems Operational',
    );
    expect(result.current.statusData.components).toHaveLength(2);
    expect(result.current.statusData.degraded_components).toHaveLength(1);
    expect(result.current.statusData.incidents).toHaveLength(1);
  });

  it('handles missing quay component gracefully', () => {
    mockStatusPage({
      components: [{id: 'other', name: 'Other', status: 'operational'}],
      incidents: [],
      scheduled_maintenances: [],
    });

    const {result} = renderHook(() => useServiceStatus());
    expect(result.current.statusData).toBeNull();
  });

  it('handles null summary data', () => {
    mockStatusPage(null);

    const {result} = renderHook(() => useServiceStatus());
    expect(result.current.statusData).toBeNull();
  });
});
