import {render, screen} from 'src/test-utils';
import DefaultPermissions from './DefaultPermissions';

vi.mock('src/components/toolbar/DropdownWithDescription', () => ({
  DropdownWithDescription: ({selectedVal, onSelect}: any) => (
    <div data-testid="mock-dropdown">{selectedVal}</div>
  ),
}));

function makeProps(overrides = {}) {
  return {
    robotName: 'myrobot',
    repoPermissions: [
      {name: 'Read', description: 'Read access'},
      {name: 'Write', description: 'Write access'},
    ],
    robotDefaultPerm: 'None',
    setRobotdefaultPerm: vi.fn(),
    ...overrides,
  };
}

describe('DefaultPermissions', () => {
  it('renders heading and description', () => {
    render(<DefaultPermissions {...makeProps()} />);
    expect(
      screen.getByText('Default permissions (Optional)'),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Default permissions panel defines permissions/),
    ).toBeInTheDocument();
  });

  it('displays robot name in Applied To field', () => {
    render(<DefaultPermissions {...makeProps()} />);
    expect(screen.getByTestId('applied-to-input')).toHaveValue('myrobot');
    expect(screen.getByTestId('applied-to-input')).toBeDisabled();
  });

  it('shows current default permission in dropdown', () => {
    render(<DefaultPermissions {...makeProps({robotDefaultPerm: 'Read'})} />);
    expect(screen.getByTestId('mock-dropdown')).toHaveTextContent('Read');
  });
});
