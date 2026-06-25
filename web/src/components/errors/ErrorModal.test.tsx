import {render, screen} from 'src/test-utils';
import ErrorModal from './ErrorModal';

describe('ErrorModal', () => {
  it('renders modal open when error is a non-null string', () => {
    render(
      <ErrorModal
        error="Something went wrong"
        setError={vi.fn()}
        title="Error"
      />,
    );
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
  });

  it('renders each item when error is an array of strings', () => {
    render(
      <ErrorModal
        error={['First error', 'Second error']}
        setError={vi.fn()}
        title="Errors"
      />,
    );
    expect(screen.getByText('First error')).toBeInTheDocument();
    expect(screen.getByText('Second error')).toBeInTheDocument();
  });

  it('modal is closed (not rendered) when error is null', () => {
    render(<ErrorModal error={null} setError={vi.fn()} title="Error" />);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('renders custom title', () => {
    render(
      <ErrorModal error="Some error" setError={vi.fn()} title="Custom Title" />,
    );
    expect(screen.getByText('Custom Title')).toBeInTheDocument();
  });
});
