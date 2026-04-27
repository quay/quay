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
    // getTimezoneLabel always returns a non-empty string
    const helper = document.querySelector('.pf-v6-c-helper-text__item');
    expect(helper).toBeInTheDocument();
    expect(helper.textContent).toMatch(/time/i);
  });

  it('renders with a pre-filled date value', () => {
    render(<FormDateTimePicker value="2024-06-15T10:30" onChange={vi.fn()} />);
    // Date picker input should have a value
    const dateInput = document.querySelector('input[aria-label="Select date"]');
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
