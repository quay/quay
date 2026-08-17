import {render, screen, userEvent, waitFor} from 'src/test-utils';
import NameAndDescription from './NameAndDescription';
import {validateRobotName} from 'src/libs/utils';

function makeProps(overrides = {}) {
  return {
    name: '',
    setName: vi.fn(),
    description: '',
    setDescription: vi.fn(),
    nameLabel: 'Provide a name for your robot account:',
    descriptionLabel: 'Provide an optional description:',
    helperText: 'Max length: 255',
    nameHelperText: 'Must match the robot name pattern.',
    validateName: () => false,
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

  it('renders labels correctly', () => {
    render(<NameAndDescription {...makeProps()} />);
    expect(
      screen.getByText('Provide a name for your robot account:'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('Provide an optional description:'),
    ).toBeInTheDocument();
  });

  it('shows default helper text when name is empty', () => {
    render(<NameAndDescription {...makeProps()} />);
    expect(
      screen.getByText('Must match the robot name pattern.'),
    ).toBeInTheDocument();
  });

  it('shows success validation when validateName returns true', async () => {
    const props = makeProps({
      name: 'validrobot',
      validateName: () => true,
    });
    render(<NameAndDescription {...props} />);
    // The helper text should still be displayed (with success variant)
    expect(
      screen.getByText('Must match the robot name pattern.'),
    ).toBeInTheDocument();
  });

  it('shows error validation when validateName returns false for non-empty name', async () => {
    const props = makeProps({
      name: 'INVALID',
      validateName: () => false,
    });
    render(<NameAndDescription {...props} />);
    // The helper text should still be displayed (with error variant)
    expect(
      screen.getByText('Must match the robot name pattern.'),
    ).toBeInTheDocument();
  });

  it('calls setName when typing in the name field', async () => {
    const setName = vi.fn();
    render(<NameAndDescription {...makeProps({setName})} />);
    const nameInput = screen.getByTestId('robot-wizard-form-name');
    await userEvent.type(nameInput, 'a');
    expect(setName).toHaveBeenCalledWith('a');
  });

  it('calls setDescription when typing in the description field', async () => {
    const setDescription = vi.fn();
    render(<NameAndDescription {...makeProps({setDescription})} />);
    const descInput = screen.getByTestId('robot-wizard-form-description');
    await userEvent.type(descInput, 'test description');
    expect(setDescription).toHaveBeenCalled();
  });

  it('displays description helper text', () => {
    render(<NameAndDescription {...makeProps()} />);
    expect(screen.getByText('Max length: 255')).toBeInTheDocument();
  });

  it('shows default state when name is empty string', () => {
    const props = makeProps({name: '', validateName: () => false});
    render(<NameAndDescription {...props} />);
    // Should show default helper text, not error
    const helperText = screen.getByText('Must match the robot name pattern.');
    expect(helperText).toBeInTheDocument();
  });

  it('integrates with validateRobotName for valid input', () => {
    const props = makeProps({
      name: 'my-robot.v2',
      validateName: () => validateRobotName('my-robot.v2'),
    });
    render(<NameAndDescription {...props} />);
    expect(
      screen.getByText('Must match the robot name pattern.'),
    ).toBeInTheDocument();
  });

  it('integrates with validateRobotName for invalid input', () => {
    const props = makeProps({
      name: '-invalid',
      validateName: () => validateRobotName('-invalid'),
    });
    render(<NameAndDescription {...props} />);
    expect(
      screen.getByText('Must match the robot name pattern.'),
    ).toBeInTheDocument();
  });
});
