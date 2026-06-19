import {render, screen} from 'src/test-utils';
import {MemoryRouter} from 'react-router-dom';
import {
  isDetailPagePath,
  QuaySidebar,
  sidebarPropsForPath,
} from './QuaySidebar';

vi.mock('src/hooks/UseQuayConfig', () => ({
  useQuayConfig: vi.fn(() => ({
    config: {BRANDING: {}},
    features: {},
  })),
}));

vi.mock('src/hooks/UseCurrentUser', () => ({
  useCurrentUser: vi.fn(() => ({
    isSuperUser: false,
  })),
}));

describe('isDetailPagePath', () => {
  it('returns false for repository list page', () => {
    expect(isDetailPagePath('/repository')).toBe(false);
  });

  it('returns false for organization list page', () => {
    expect(isDetailPagePath('/organization')).toBe(false);
  });

  it('returns true for repository detail page', () => {
    expect(isDetailPagePath('/repository/myorg/myrepo')).toBe(true);
  });

  it('returns true for repository detail sub-routes', () => {
    expect(isDetailPagePath('/repository/myorg/myrepo/tag/latest')).toBe(true);
    expect(
      isDetailPagePath('/repository/myorg/myrepo/manifest/sha256:abc'),
    ).toBe(true);
    expect(isDetailPagePath('/repository/myorg/myrepo/trigger/uuid-123')).toBe(
      true,
    );
    expect(isDetailPagePath('/repository/myorg/myrepo/build/build-456')).toBe(
      true,
    );
  });

  it('returns true for organization detail page', () => {
    expect(isDetailPagePath('/organization/myorg')).toBe(true);
  });

  it('returns false for organization team sub-route', () => {
    expect(isDetailPagePath('/organization/myorg/teams/devs')).toBe(false);
  });

  it('returns false for superuser pages', () => {
    expect(isDetailPagePath('/service-keys')).toBe(false);
    expect(isDetailPagePath('/change-log')).toBe(false);
    expect(isDetailPagePath('/usage-logs')).toBe(false);
  });

  it('returns false for overview page', () => {
    expect(isDetailPagePath('/overview')).toBe(false);
  });

  it('returns false for root path', () => {
    expect(isDetailPagePath('/')).toBe(false);
  });
});

describe('sidebarPropsForPath', () => {
  it('returns sidebar component and managed sidebar on list pages', () => {
    const props = sidebarPropsForPath('/repository');
    expect(props.sidebar).not.toBeNull();
    expect(props.isManagedSidebar).toBe(true);
  });

  it('returns null sidebar on repository detail pages', () => {
    const props = sidebarPropsForPath('/repository/myorg/myrepo');
    expect(props.sidebar).toBeNull();
    expect(props.isManagedSidebar).toBe(false);
  });

  it('returns null sidebar on organization detail pages', () => {
    const props = sidebarPropsForPath('/organization/myorg');
    expect(props.sidebar).toBeNull();
    expect(props.isManagedSidebar).toBe(false);
  });
});

describe('QuaySidebar', () => {
  it('renders sidebar on list pages', () => {
    render(
      <MemoryRouter initialEntries={['/repository']}>
        <QuaySidebar />
      </MemoryRouter>,
    );
    expect(screen.getByText('Repositories')).toBeInTheDocument();
  });
});
