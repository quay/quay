import React from 'react';
import {useForm} from 'react-hook-form';
import {render, screen, userEvent} from 'src/test-utils';
import {OrgMirroringRobotUser} from './OrgMirroringRobotUser';
import {OrgMirroringFormData} from './types';
import {Entity} from 'src/resources/UserResource';

vi.mock('src/components/EntitySearch', () => ({
  __esModule: true,
  default: (props: {
    onSelect: (e: Entity) => void;
    onClear: () => void;
    onError: () => void;
    value?: string;
    placeholderText?: string;
  }) => (
    <div data-testid="entity-search">
      <input
        data-testid="robot-input"
        value={props.value ?? ''}
        placeholder={props.placeholderText}
        readOnly
      />
      <button
        data-testid="select-robot"
        onClick={() =>
          props.onSelect({
            name: 'testorg+buildbot',
            kind: 'robot',
            is_robot: true,
          })
        }
      >
        Select
      </button>
      <button data-testid="clear-robot" onClick={() => props.onClear()}>
        Clear
      </button>
      <button data-testid="trigger-error" onClick={() => props.onError()}>
        Error
      </button>
    </div>
  ),
}));

const defaultFormValues: OrgMirroringFormData = {
  isEnabled: false,
  externalRegistryType: '',
  externalRegistryUrl: '',
  externalNamespace: '',
  robotUsername: '',
  visibility: 'public',
  repositoryFilters: '',
  syncStartDate: '',
  syncValue: '',
  syncUnit: 'minutes',
  username: '',
  password: '',
  verifyTls: true,
  httpProxy: '',
  httpsProxy: '',
  noProxy: '',
  skopeoTimeout: null,
};

function TestHarness({
  selectedRobot = null,
  onSetSelectedRobot,
  onAddAlert,
}: {
  selectedRobot?: Entity | null;
  onSetSelectedRobot?: (robot: Entity | null) => void;
  onAddAlert?: (alert: any) => void;
}) {
  const {control, formState} = useForm<OrgMirroringFormData>({
    defaultValues: defaultFormValues,
  });
  return (
    <OrgMirroringRobotUser
      control={control}
      errors={formState.errors}
      orgName="testorg"
      selectedRobot={selectedRobot}
      setSelectedRobot={onSetSelectedRobot ?? vi.fn()}
      robotOptions={[]}
      addAlert={onAddAlert ?? vi.fn()}
    />
  );
}

describe('OrgMirroringRobotUser', () => {
  it('renders the Robot User label with a required indicator', () => {
    const {container} = render(<TestHarness />);
    expect(screen.getByText('Robot User')).toBeInTheDocument();
    const asterisk = container.querySelector('.pf-v6-c-form__label-required');
    expect(asterisk).toBeInTheDocument();
    expect(asterisk?.textContent).toContain('*');
  });

  it('renders the entity search component', () => {
    render(<TestHarness />);
    expect(screen.getByTestId('entity-search')).toBeInTheDocument();
  });

  it('passes the selected robot value to EntitySearch', () => {
    render(
      <TestHarness
        selectedRobot={{
          name: 'testorg+buildbot',
          kind: 'robot',
          is_robot: true,
        }}
      />,
    );
    expect(screen.getByTestId('robot-input')).toHaveValue('testorg+buildbot');
  });

  it('calls setSelectedRobot with the entity on selection', async () => {
    const setSelectedRobot = vi.fn();
    render(<TestHarness onSetSelectedRobot={setSelectedRobot} />);
    await userEvent.click(screen.getByTestId('select-robot'));
    expect(setSelectedRobot).toHaveBeenCalledWith(
      expect.objectContaining({name: 'testorg+buildbot'}),
    );
  });

  it('calls setSelectedRobot(null) on clear', async () => {
    const setSelectedRobot = vi.fn();
    render(<TestHarness onSetSelectedRobot={setSelectedRobot} />);
    await userEvent.click(screen.getByTestId('clear-robot'));
    expect(setSelectedRobot).toHaveBeenCalledWith(null);
  });

  it('calls addAlert with failure variant on EntitySearch error', async () => {
    const addAlert = vi.fn();
    render(<TestHarness onAddAlert={addAlert} />);
    await userEvent.click(screen.getByTestId('trigger-error'));
    expect(addAlert).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'Error loading robot users',
      }),
    );
  });
});
