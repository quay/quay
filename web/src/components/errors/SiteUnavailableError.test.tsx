import {render, screen} from 'src/test-utils';
import SiteUnavailableError from './SiteUnavailableError';

const originalLocation = window.location;

afterEach(() => {
  Object.defineProperty(window, 'location', {
    configurable: true,
    value: originalLocation,
  });
});

describe('SiteUnavailableError', () => {
  it('renders "This site is temporarily unavailable" heading', () => {
    render(<SiteUnavailableError />);
    expect(
      screen.getByText('This site is temporarily unavailable'),
    ).toBeInTheDocument();
  });

  it('renders quay.io status page link when hostname is quay.io', () => {
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: {hostname: 'quay.io', reload: vi.fn()},
    });
    render(<SiteUnavailableError />);
    expect(screen.getByRole('link', {name: 'status page'})).toBeInTheDocument();
  });

  it('renders generic message for non-quay.io hostname', () => {
    render(<SiteUnavailableError />);
    expect(
      screen.getByText(/contact your organization administrator\./i),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole('link', {name: 'status page'}),
    ).not.toBeInTheDocument();
  });

  it('renders Reload button that calls window.location.reload', () => {
    const reload = vi.fn();
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: {hostname: 'localhost', reload},
    });
    render(<SiteUnavailableError />);
    screen.getByRole('button', {name: /reload/i}).click();
    expect(reload).toHaveBeenCalledTimes(1);
  });
});
