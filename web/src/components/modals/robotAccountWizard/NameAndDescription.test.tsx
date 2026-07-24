import {render, screen, userEvent, waitFor} from 'src/test-utils';
import NameAndDescription from './NameAndDescription';

function makeProps(overrides = {}) {
  return {
    name: '',
    setName: vi.fn(),
    description: '',
    setDescription: vi.fn(),
    nameLabel: 'Robot name:',
    descriptionLabel: 'Robot description:',
    helperText: 'Enter a description for the robot',
    nameHelperText: 'Must match ^[a-z][a-z0-9_]{1,254}$',
    validateName: vi.fn().mockReturnValue(false),
    ...overrides,
  };
}

describe('NameAndDescription', () => {
  it('renders name and description inputs', () => {
    render(<NameAndDescription {...makeProps()} />);
    expect(screen.getByTestId('robot-wizard-form-name')).toBeInTheDocument();
    expect(
      screen.getByTestId('robot-wizard-form-description'),
    ).toBeInTheDocument();
  });

  it('displays labels', () => {
    render(<NameAndDescription {...makeProps()} />);
    expect(screen.getByText('Robot name:')).toBeInTheDocument();
    expect(screen.getByText('Robot description:')).toBeInTheDocument();
  });

  it('calls setName when name input changes', async () => {
    const setName = vi.fn();
    render(<NameAndDescription {...makeProps({setName})} />);
    await userEvent.type(screen.getByTestId('robot-wizard-form-name'), 'a');
    expect(setName).toHaveBeenCalledWith('a');
  });

  it('calls setDescription when description input changes', async () => {
    const setDescription = vi.fn();
    render(<NameAndDescription {...makeProps({setDescription})} />);
    await userEvent.type(
      screen.getByTestId('robot-wizard-form-description'),
      'test desc',
    );
    expect(setDescription).toHaveBeenCalled();
  });

  it('shows error state when name is invalid', () => {
    const validateName = vi.fn().mockReturnValue(false);
    render(
      <NameAndDescription {...makeProps({name: 'INVALID', validateName})} />,
    );
    expect(screen.getByTestId('robot-wizard-form-name')).toHaveAttribute(
      'aria-invalid',
      'true',
    );
  });

  it('shows success state when name is valid', () => {
    const validateName = vi.fn().mockReturnValue(true);
    render(
      <NameAndDescription {...makeProps({name: 'validname', validateName})} />,
    );
    expect(screen.getByTestId('robot-wizard-form-name')).not.toHaveAttribute(
      'aria-invalid',
      'true',
    );
  });
});
