import {render, screen} from 'src/test-utils';
import DeleteDefaultPermissionKebab from './DeleteDefaultPermissionKebab';
import type {IDefaultPermission} from 'src/hooks/UseDefaultPermissions';

const mockUseSuperuserPermissions = vi.hoisted(() =>
  vi.fn(() => ({isReadOnlySuperUser: false})),
);

vi.mock('src/hooks/UseSuperuserPermissions', () => ({
  useSuperuserPermissions: mockUseSuperuserPermissions,
}));

vi.mock('src/hooks/UseDefaultPermissions', () => ({
  useDeleteDefaultPermission: () => ({
    removeDefaultPermission: vi.fn(),
    errorDeleteDefaultPermission: false,
    successDeleteDefaultPermission: false,
  }),
}));

const defaultPermission = {
  id: 1,
  createdBy: 'testuser',
  appliedTo: 'org+robot',
  permission: 'read',
} as unknown as IDefaultPermission;

describe('DeleteDefaultPermissionKebab', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseSuperuserPermissions.mockReturnValue({isReadOnlySuperUser: false});
  });

  it('renders kebab for non-readonly user', () => {
    render(
      <DeleteDefaultPermissionKebab
        orgName="myorg"
        defaultPermission={defaultPermission}
      />,
    );
    expect(
      screen.getByTestId(`${defaultPermission.createdBy}-toggle-kebab`),
    ).toBeInTheDocument();
  });

  it('returns null for readonly superuser', () => {
    mockUseSuperuserPermissions.mockReturnValue({isReadOnlySuperUser: true});
    const {container} = render(
      <DeleteDefaultPermissionKebab
        orgName="myorg"
        defaultPermission={defaultPermission}
      />,
    );
    expect(container.firstChild).toBeNull();
  });
});
