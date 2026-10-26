import React from 'react';
import {useForm} from 'react-hook-form';
import {render, screen, userEvent} from 'src/test-utils';
import {MirroringConfiguration} from './MirroringConfiguration';
import {MirroringFormData} from './types';

vi.mock('src/resources/MirroringResource', () => ({
  getMirrorConfig: vi.fn(),
  toggleMirroring: vi.fn(),
  syncMirror: vi.fn(),
}));

vi.mock('src/components/EntitySearch', () => ({
  __esModule: true,
  default: () => <div data-testid="entity-search" />,
}));

vi.mock('src/components/forms/FormTextInput', () => ({
  FormTextInput: ({label}: {label: string}) => <div>{label}</div>,
}));

vi.mock('src/components/forms/FormCheckbox', () => ({
  FormCheckbox: () => <div data-testid="form-checkbox" />,
}));

vi.mock('src/components/FormDateTimePicker', () => ({
  FormDateTimePicker: () => <div data-testid="datetime-picker" />,
}));

vi.mock('./ArchitectureFilter', () => ({
  ArchitectureFilter: () => <div data-testid="arch-filter" />,
}));

const defaultFormValues: MirroringFormData = {
  isEnabled: true,
  externalReference: '',
  tags: '',
  syncStartDate: '',
  syncValue: '24',
  syncUnit: 'hours',
  robotUsername: '',
  username: '',
  password: '',
  verifyTls: false,
  httpProxy: '',
  httpsProxy: '',
  noProxy: '',
  unsignedImages: false,
  skopeoTimeoutInterval: 300,
  architectureFilter: [],
};

function TestHarness({
  onFormChange,
}: {
  onFormChange?: (values: MirroringFormData) => void;
}) {
  const {control, formState, watch} = useForm<MirroringFormData>({
    defaultValues: defaultFormValues,
    mode: 'onChange',
  });
  const formValues = watch();

  React.useEffect(() => {
    onFormChange?.(formValues);
  }, [formValues, onFormChange]);

  return (
    <MirroringConfiguration
      control={control}
      errors={formState.errors}
      formValues={formValues}
      config={null}
      namespace="testorg"
      repoName="testrepo"
      selectedRobot={null}
      setSelectedRobot={vi.fn()}
      isSelectOpen={false}
      setIsSelectOpen={vi.fn()}
      isHovered={false}
      setIsHovered={vi.fn()}
      robotOptions={[]}
      setConfig={vi.fn()}
      addAlert={vi.fn()}
      architectureFilter={[]}
      setArchitectureFilter={vi.fn()}
    />
  );
}

describe('MirroringConfiguration - skopeo timeout interval', () => {
  it('renders with the default timeout value', () => {
    render(<TestHarness />);
    const input = screen.getByTestId('skopeo-timeout-input');
    expect(input).toHaveValue(300);
  });

  it('clears the field to empty when user deletes the value', async () => {
    render(<TestHarness />);
    const input = screen.getByTestId('skopeo-timeout-input');
    await userEvent.clear(input);
    expect(input).toHaveValue(null);
  });

  it('does not snap back to 300 after clearing', async () => {
    render(<TestHarness />);
    const input = screen.getByTestId('skopeo-timeout-input');
    await userEvent.clear(input);
    expect(input).not.toHaveValue(300);
  });

  it('accepts a new numeric value typed after clearing', async () => {
    render(<TestHarness />);
    const input = screen.getByTestId('skopeo-timeout-input');
    await userEvent.clear(input);
    await userEvent.type(input, '600');
    expect(input).toHaveValue(600);
  });

  it('shows validation error when field is below minimum', async () => {
    render(<TestHarness />);
    const input = screen.getByTestId('skopeo-timeout-input');
    await userEvent.clear(input);
    await userEvent.type(input, '100');
    expect(
      await screen.findByText(/Minimum timeout is 300 seconds/),
    ).toBeInTheDocument();
  });
});
