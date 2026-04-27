import {render, screen} from 'src/test-utils';
import {FormDateTimePicker} from './FormDateTimePicker';

describe('FormDateTimePicker', () => {
  it('renders the date picker input', () => {
    render(
      <FormDateTimePicker
        value=""
        onChange={vi.fn()}
        dateAriaLabel="Select date"
      />,
    );
    expect(screen.getByLabelText('Select date')).toBeInTheDocument();
  });

  it('renders the time picker with custom aria-label', () => {
    render(
      <FormDateTimePicker
        value=""
        onChange={vi.fn()}
        timeAriaLabel="Select time"
      />,
    );
    expect(screen.getByLabelText('Select time')).toBeInTheDocument();
  });

  it('displays the timezone label helper text', () => {
    render(<FormDateTimePicker value="2024-06-15T10:30" onChange={vi.fn()} />);
    expect(screen.getByText(/all times are shown in/i)).toBeInTheDocument();
  });

  it('renders with a pre-filled date value', () => {
    // '2024-06-15T10:30' is treated as local time; 10:30 AM is safe across all populated timezones
    render(<FormDateTimePicker value="2024-06-15T10:30" onChange={vi.fn()} />);
    const dateInput = screen.getByLabelText('Select date');
    expect(dateInput).toBeInTheDocument();
    expect(dateInput).toHaveValue('2024-06-15');
  });

  it('renders with empty value without crashing', () => {
    const {container} = render(
      <FormDateTimePicker value="" onChange={vi.fn()} />,
    );
    expect(container).toBeInTheDocument();
  });

  it('uses default aria-labels when not provided', () => {
    render(<FormDateTimePicker value="" onChange={vi.fn()} />);
    expect(screen.getByLabelText('Select date')).toBeInTheDocument();
    expect(screen.getByLabelText('Select time')).toBeInTheDocument();
  });
});
