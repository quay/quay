import {render, screen, userEvent} from 'src/test-utils';
import {useForm} from 'react-hook-form';
import {FormCheckbox} from './FormCheckbox';

type TestForm = {
  enabled: boolean;
};

function TestWrapper({
  defaultValue = false,
  description,
  customOnChange,
}: {
  defaultValue?: boolean;
  description?: string;
  customOnChange?: (checked: boolean, onChange: (v: boolean) => void) => void;
}) {
  const {control} = useForm<TestForm>({
    defaultValues: {enabled: defaultValue},
  });
  return (
    <FormCheckbox
      name="enabled"
      control={control}
      label="Enable feature"
      description={description}
      customOnChange={customOnChange}
    />
  );
}

describe('FormCheckbox', () => {
  it('renders the checkbox label', () => {
    render(<TestWrapper />);
    expect(screen.getByText('Enable feature')).toBeInTheDocument();
  });

  it('starts unchecked by default', () => {
    render(<TestWrapper />);
    expect(screen.getByRole('checkbox')).not.toBeChecked();
  });

  it('starts checked when defaultValue is true', () => {
    render(<TestWrapper defaultValue={true} />);
    expect(screen.getByRole('checkbox')).toBeChecked();
  });

  it('toggles checked state on click', async () => {
    render(<TestWrapper />);
    const checkbox = screen.getByRole('checkbox');
    await userEvent.click(checkbox);
    expect(checkbox).toBeChecked();
    await userEvent.click(checkbox);
    expect(checkbox).not.toBeChecked();
  });

  it('renders description text when provided', () => {
    render(<TestWrapper description="This enables the new UI" />);
    expect(screen.getByText('This enables the new UI')).toBeInTheDocument();
  });
});
