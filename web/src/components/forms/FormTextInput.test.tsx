import {render, screen, userEvent} from 'src/test-utils';
import {useForm} from 'react-hook-form';
import {FormTextInput} from './FormTextInput';

type TestForm = {
  username: string;
  password: string;
};

function TestWrapper({
  required = false,
  type = 'text' as const,
  helperText,
  placeholder,
  customValidation,
  disabled = false,
  showNoneWhenEmpty = false,
  autoComplete,
}: {
  required?: boolean;
  type?: 'text' | 'password';
  helperText?: string;
  placeholder?: string;
  customValidation?: (v: string) => string | boolean;
  disabled?: boolean;
  showNoneWhenEmpty?: boolean;
  autoComplete?: string;
}) {
  const {
    control,
    formState: {errors},
  } = useForm<TestForm>({defaultValues: {username: ''}});
  return (
    <FormTextInput
      name="username"
      control={control}
      errors={errors}
      label="Username"
      required={required}
      type={type}
      helperText={helperText}
      placeholder={placeholder}
      customValidation={customValidation}
      disabled={disabled}
      showNoneWhenEmpty={showNoneWhenEmpty}
      autoComplete={autoComplete}
    />
  );
}

describe('FormTextInput', () => {
  it('renders the label', () => {
    render(<TestWrapper />);
    expect(screen.getByText('Username')).toBeInTheDocument();
  });

  it('renders the input as text type by default', () => {
    render(<TestWrapper />);
    expect(screen.getByRole('textbox')).toHaveAttribute('type', 'text');
  });

  it('renders a password input when type is password', () => {
    render(<TestWrapper type="password" />);
    const input = document.querySelector('input[type="password"]');
    expect(input).toBeInTheDocument();
  });

  it('renders placeholder text', () => {
    render(<TestWrapper placeholder="Enter username" />);
    expect(screen.getByPlaceholderText('Enter username')).toBeInTheDocument();
  });

  it('shows "None" placeholder when showNoneWhenEmpty and no placeholder', () => {
    render(<TestWrapper showNoneWhenEmpty />);
    expect(screen.getByPlaceholderText('None')).toBeInTheDocument();
  });

  it('renders helper text when no errors', () => {
    render(<TestWrapper helperText="Max 64 characters" />);
    expect(screen.getByText('Max 64 characters')).toBeInTheDocument();
  });

  it('renders as disabled when disabled is true', () => {
    render(<TestWrapper disabled />);
    expect(screen.getByRole('textbox')).toBeDisabled();
  });

  it('accepts user input', async () => {
    render(<TestWrapper />);
    const input = screen.getByRole('textbox');
    await userEvent.type(input, 'myuser');
    expect(input).toHaveValue('myuser');
  });

  it('applies autoComplete attribute when provided', () => {
    render(<TestWrapper autoComplete="off" />);
    expect(screen.getByRole('textbox')).toHaveAttribute('autocomplete', 'off');
  });

  it('applies autoComplete new-password when provided', () => {
    render(<TestWrapper type="password" autoComplete="new-password" />);
    const input = document.querySelector('input[type="password"]');
    expect(input).toHaveAttribute('autocomplete', 'new-password');
  });
});
