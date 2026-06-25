import {render, screen} from 'src/test-utils';
import RequestError from './RequestError';

const originalLocation = window.location;

afterEach(() => {
  Object.defineProperty(window, 'location', {
    configurable: true,
    value: originalLocation,
  });
});

describe('RequestError', () => {
  it('renders default title when none provided', () => {
    render(<RequestError message="Something failed" />);
    expect(screen.getByText('Unable to complete request')).toBeInTheDocument();
  });

  it('renders custom title when provided', () => {
    render(<RequestError message="Oops" title="Custom Error Title" />);
    expect(screen.getByText('Custom Error Title')).toBeInTheDocument();
  });

  it('renders message with first letter capitalised', () => {
    render(<RequestError message="something went wrong" />);
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
  });

  it('extracts message from plain Error when no message prop', () => {
    render(<RequestError err={new Error('plain error occurred')} />);
    expect(screen.getByText('Plain error occurred')).toBeInTheDocument();
  });

  it('renders Retry button that calls window.location.reload', () => {
    const reload = vi.fn();
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: {...originalLocation, reload},
    });
    render(<RequestError message="err" />);
    screen.getByRole('button', {name: /retry/i}).click();
    expect(reload).toHaveBeenCalledTimes(1);
  });
});
