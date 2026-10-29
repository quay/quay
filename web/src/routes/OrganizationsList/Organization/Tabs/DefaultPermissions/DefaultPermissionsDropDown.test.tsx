import {render, screen} from 'src/test-utils';
import DefaultPermissionsDropDown from './DefaultPermissionsDropDown';
import type {IDefaultPermission} from 'src/hooks/UseDefaultPermissions';

const mockUseSuperuserPermissions = vi.hoisted(() =>
  vi.fn(() => ({isReadOnlySuperUser: false})),
);

vi.mock('src/hooks/UseSuperuserPermissions', () => ({
  useSuperuserPermissions: mockUseSuperuserPermissions,
}));

vi.mock('src/hooks/UseDefaultPermissions', () => ({
  useUpdateDefaultPermission: () => ({
    setDefaultPermission: vi.fn(),
    successSetDefaultPermission: false,
    errorSetDefaultPermission: false,
  }),
}));

const defaultPermission = {
  id: 1,
  createdBy: 'testuser',
  appliedTo: 'org+robot',
  permission: 'read',
};

describe('DefaultPermissionsDropDown', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseSuperuserPermissions.mockReturnValue({isReadOnlySuperUser: false});
  });

  it('renders dropdown toggle with permission level', () => {
    render(
      <DefaultPermissionsDropDown
        orgName="myorg"
        defaultPermission={defaultPermission as unknown as IDefaultPermission}
      />,
    );
    expect(
      screen.getByTestId(
        `${defaultPermission.createdBy}-permission-dropdown-toggle`,
      ),
    ).toBeInTheDocument();
  });

  it('dropdown toggle is enabled for non-readonly user', () => {
    render(
      <DefaultPermissionsDropDown
        orgName="myorg"
        defaultPermission={defaultPermission as unknown as IDefaultPermission}
      />,
    );
    const toggle = screen.getByTestId(
      `${defaultPermission.createdBy}-permission-dropdown-toggle`,
    );
    expect(toggle).not.toBeDisabled();
  });

  it('dropdown toggle is disabled for readonly superuser', () => {
    mockUseSuperuserPermissions.mockReturnValue({isReadOnlySuperUser: true});
    render(
      <DefaultPermissionsDropDown
        orgName="myorg"
        defaultPermission={defaultPermission as unknown as IDefaultPermission}
      />,
    );
    const toggle = screen.getByTestId(
      `${defaultPermission.createdBy}-permission-dropdown-toggle`,
    );
    expect(toggle).toBeDisabled();
  });
});
