import {render, screen} from 'src/test-utils';
import ErrorBoundary from './ErrorBoundary';

describe('ErrorBoundary', () => {
  it('renders children when no error', () => {
    render(
      <ErrorBoundary fallback={<span>Error fallback</span>}>
        <span>Child content</span>
      </ErrorBoundary>,
    );
    expect(screen.getByText('Child content')).toBeInTheDocument();
    expect(screen.queryByText('Error fallback')).not.toBeInTheDocument();
  });

  it('renders fallback when hasError prop is true', () => {
    render(
      <ErrorBoundary fallback={<span>Error fallback</span>} hasError>
        <span>Child content</span>
      </ErrorBoundary>,
    );
    expect(screen.getByText('Error fallback')).toBeInTheDocument();
    expect(screen.queryByText('Child content')).not.toBeInTheDocument();
  });

  it('renders fallback when child throws during render', () => {
    const ThrowingChild = () => {
      throw new Error('Test error');
    };
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(vi.fn());
    render(
      <ErrorBoundary fallback={<span>Error fallback</span>}>
        <ThrowingChild />
      </ErrorBoundary>,
    );
    expect(screen.getByText('Error fallback')).toBeInTheDocument();
    consoleSpy.mockRestore();
  });

  it('accepts JSX as fallback', () => {
    render(<ErrorBoundary fallback={<button>Retry</button>} hasError />);
    expect(screen.getByRole('button', {name: 'Retry'})).toBeInTheDocument();
  });

  it('renders nothing for children when hasError is false', () => {
    const {container} = render(
      <ErrorBoundary fallback={<span>Fallback</span>} hasError={false}>
        <div>visible</div>
      </ErrorBoundary>,
    );
    expect(container).toHaveTextContent('visible');
    expect(screen.queryByText('Fallback')).not.toBeInTheDocument();
  });
});
