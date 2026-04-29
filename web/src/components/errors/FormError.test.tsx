import {render, screen, userEvent} from 'src/test-utils';
import FormError from './FormError';

describe('FormError', () => {
  it('renders nothing when message is not an error string', () => {
    const {container} = render(<FormError message="" setErr={vi.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders danger alert with the error message', () => {
    render(<FormError message="Validation failed" setErr={vi.fn()} />);
    expect(screen.getByText('Validation failed')).toBeInTheDocument();
    expect(document.getElementById('form-error-alert')).toBeInTheDocument();
  });

  it('calls setErr with empty string when close button clicked', async () => {
    const setErr = vi.fn();
    render(<FormError message="Some error" setErr={setErr} />);
    await userEvent.click(screen.getByRole('button', {name: /close/i}));
    expect(setErr).toHaveBeenCalledWith('');
  });
});
