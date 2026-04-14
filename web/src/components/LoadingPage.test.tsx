import {LoadingPage} from './LoadingPage';
import {render, screen} from 'src/test-utils';

describe('LoadingPage', () => {
  it('renders default loading state', () => {
    render(<LoadingPage />);
    expect(screen.getByText('Loading')).toBeInTheDocument();
  });

  it('renders custom title', () => {
    render(<LoadingPage title="Fetching data" />);
    expect(screen.getByText('Fetching data')).toBeInTheDocument();
  });

  it('renders custom message', () => {
    render(<LoadingPage message="Please wait..." />);
    expect(screen.getByText('Please wait...')).toBeInTheDocument();
  });

  it('renders JSX title', () => {
    render(<LoadingPage title={<span>Custom JSX</span>} />);
    expect(screen.getByText('Custom JSX')).toBeInTheDocument();
  });

  it('renders primary action', () => {
    render(<LoadingPage primaryAction={<button>Retry</button>} />);
    expect(screen.getByRole('button', {name: 'Retry'})).toBeInTheDocument();
  });

  it('renders secondary actions', () => {
    render(<LoadingPage secondaryActions={<button>Cancel</button>} />);
    expect(screen.getByRole('button', {name: 'Cancel'})).toBeInTheDocument();
  });
});
