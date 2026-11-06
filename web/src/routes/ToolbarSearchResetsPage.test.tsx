import {fireEvent} from '@testing-library/react';
import {render, screen} from 'src/test-utils';
import {SearchState} from 'src/components/toolbar/SearchTypes';
import DefaultPermissionsToolbar from './OrganizationsList/Organization/Tabs/DefaultPermissions/DefaultPermissionsToolbar';
import OAuthApplicationsToolbar from './OrganizationsList/Organization/Tabs/OAuthApplications/OAuthApplicationsToolbar';
import ApplicationTokensToolbar from './OrganizationsList/Organization/Tabs/Settings/ApplicationTokensToolbar';
import CollaboratorsViewToolbar from './OrganizationsList/Organization/Tabs/TeamsAndMembership/CollaboratorsView/CollaboratorsViewToolbar';
import MembersViewToolbar from './OrganizationsList/Organization/Tabs/TeamsAndMembership/MembersView/MembersViewToolbar';
import ManageMembersToolbar from './OrganizationsList/Organization/Tabs/TeamsAndMembership/TeamsView/ManageMembers/ManageMembersToolbar';
import SetRepoPermissionsForTeamModalToolbar from './OrganizationsList/Organization/Tabs/TeamsAndMembership/TeamsView/SetRepoPermissionsModal/SetRepoPermissionsForTeamToolbar';
import TeamsViewToolbar from './OrganizationsList/Organization/Tabs/TeamsAndMembership/TeamsView/TeamsViewToolbar';
import {RobotAccountsToolBar} from './RepositoriesList/RobotAccountsToolBar';
import PermissionsToolbar from './RepositoryDetails/Settings/PermissionsToolbar';
import TagHistoryToolBar from './RepositoryDetails/TagHistory/TagHistoryToolbar';

function baseProps() {
  return {
    page: 2,
    setPage: vi.fn(),
    perPage: 20,
    setPerPage: vi.fn(),
    search: {query: '', field: 'name'} as SearchState,
    setSearch: vi.fn(),
    searchOptions: ['name'],
    allItems: [],
    allItemsList: [],
    paginatedItems: [],
    itemsPerPageList: [],
    filteredTokens: [],
    selectedItems: [],
    selectedMembers: [],
    selectedTeams: [],
    selectedRepoPerms: [],
    deSelectAll: vi.fn(),
    deselectAll: vi.fn(),
    setSelectedRobotAccounts: vi.fn(),
    onItemSelect: vi.fn(),
    setDrawerContent: vi.fn(),
    handleBulkDeleteModalToggle: vi.fn(),
    handleCreateModalToggle: vi.fn(),
    handleModalToggle: vi.fn(),
    totalItems: 0,
    total: 0,
    isReadOnly: false,
    isAdmin: true,
    displaySyncDirectory: false,
    isDirectoryTeamSyncModalOpen: false,
    toggleDirectoryTeamSyncModal: vi.fn(),
    pageInReadOnlyMode: false,
    isRemoveTeamSyncModalOpen: false,
    toggleRemoveTeamSyncModal: vi.fn(),
    isKebabOpen: false,
    setKebabOpen: vi.fn(),
    kebabItems: [],
    updateModifiedRepoPerms: vi.fn(),
    deleteKebabIsOpen: false,
    deleteModal: () => ({}),
    setDeleteModalOpen: vi.fn(),
    isSetRepoPermModalOpen: false,
    setRepoPermModal: {},
    buttonText: 'Create robot account',
    pageModal: {},
    isModalOpen: false,
    setModalOpen: vi.fn(),
    expandTable: vi.fn(),
    collapseTable: vi.fn(),
    org: 'org',
    repo: 'repo',
  };
}

type Props = ReturnType<typeof baseProps>;

const toolbars: [string, string, (props: Props) => React.ReactElement][] = [
  [
    'DefaultPermissionsToolbar',
    'default-permissions-search',
    (p) => <DefaultPermissionsToolbar {...p} />,
  ],
  [
    'OAuthApplicationsToolbar',
    'default-permissions-search',
    (p) => <OAuthApplicationsToolbar {...p} />,
  ],
  [
    'ApplicationTokensToolbar',
    'application-tokens-search',
    (p) => <ApplicationTokensToolbar {...p} />,
  ],
  [
    'CollaboratorsViewToolbar',
    'collaborators-view-search',
    (p) => <CollaboratorsViewToolbar {...p} />,
  ],
  [
    'MembersViewToolbar',
    'members-view-search',
    (p) => <MembersViewToolbar {...p} />,
  ],
  [
    'ManageMembersToolbar',
    'team-member-search-input',
    (p) => <ManageMembersToolbar {...p} />,
  ],
  [
    'SetRepoPermissionsForTeamModalToolbar',
    'set-repo-perm-for-team-search',
    (p) => <SetRepoPermissionsForTeamModalToolbar {...p} />,
  ],
  ['TeamsViewToolbar', 'teams-view-search', (p) => <TeamsViewToolbar {...p} />],
  [
    'RobotAccountsToolBar',
    'robot-account-search',
    (p) => <RobotAccountsToolBar {...p} />,
  ],
  [
    'PermissionsToolbar',
    'permissions-search-input',
    (p) => <PermissionsToolbar {...p} />,
  ],
];

describe.each(toolbars)('%s', (_name, searchTestId, renderToolbar) => {
  it('resets to page 1 when the search query changes', () => {
    const props = baseProps();
    render(renderToolbar(props));

    fireEvent.change(screen.getByTestId(searchTestId), {
      target: {value: 'needle'},
    });

    expect(props.setPage).toHaveBeenCalledWith(1);
    expect(props.setSearch).toHaveBeenCalledTimes(1);
    const update = props.setSearch.mock.calls[0][0];
    expect(update(props.search)).toEqual({query: 'needle', field: 'name'});
  });
});

describe('TagHistoryToolBar', () => {
  it('resets to page 1 when the search query changes', () => {
    const props = baseProps();
    const setQuery = vi.fn();
    render(
      <TagHistoryToolBar
        {...props}
        showFuture={false}
        setShowFuture={vi.fn()}
        query=""
        setQuery={setQuery}
        startTime={null}
        setStartTime={vi.fn()}
        endTime={null}
        setEndTime={vi.fn()}
      />,
    );

    fireEvent.change(screen.getByPlaceholderText('Search by tag name...'), {
      target: {value: 'needle'},
    });

    expect(setQuery).toHaveBeenCalledWith('needle');
    expect(props.setPage).toHaveBeenCalledWith(1);
  });
});
