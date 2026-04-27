import {render, screen} from 'src/test-utils';
import PageLoadError from './PageLoadError';

const originalLocation = window.location;

afterEach(() => {
  Object.defineProperty(window, 'location', {
    configurable: true,
    value: originalLocation,
  });
});

describe('PageLoadError', () => {
  it('renders "Unable to reach server" heading', () => {
    render(<PageLoadError />);
    expect(screen.getByText('Unable to reach server')).toBeInTheDocument();
  });

  it('renders the body message', () => {
    render(<PageLoadError />);
    expect(screen.getByText('Page could not be loaded')).toBeInTheDocument();
  });

  it('renders a Retry button that triggers reload', () => {
    const reload = vi.fn();
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: {...originalLocation, reload},
    });
    render(<PageLoadError />);
    screen.getByRole('button', {name: /retry/i}).click();
    expect(reload).toHaveBeenCalledTimes(1);
  });
});
