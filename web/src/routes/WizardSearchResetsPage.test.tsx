import {fireEvent} from '@testing-library/react';
import {render, screen} from 'src/test-utils';
import AddToRepository from 'src/components/modals/robotAccountWizard/AddToRepository';
import TeamView from 'src/components/modals/robotAccountWizard/TeamView';
import {
  useAnalyzeBuildTrigger,
  useGitNamespaces,
  useGitSources,
} from 'src/hooks/UseBuildTriggers';
import HostedRepository from './RepositoryDetails/Builds/BuildTriggerSetupWizardHostedRepository';
import SelectOrganization from './RepositoryDetails/Builds/BuildTriggerSetupWizardOrganization';
import RobotAccounts from './RepositoryDetails/Builds/BuildTriggerSetupWizardRobotAccounts';

vi.mock('src/hooks/UseBuildTriggers', () => ({
  useAnalyzeBuildTrigger: vi.fn(),
  useGitNamespaces: vi.fn(),
  useGitSources: vi.fn(),
}));

vi.mock('src/hooks/useRobotAccounts', () => ({
  useFetchRobotAccounts: () => ({
    robots: [],
    isLoadingRobots: false,
    isError: false,
  }),
}));

vi.mock('src/hooks/UseQuayConfig', () => ({
  useQuayConfig: () => ({
    config: {},
    oauth: {GITHUB_TRIGGER_CONFIG: {GITHUB_ENDPOINT: '', CLIENT_ID: ''}},
  }),
}));

// 21 rows at 20 per page puts item00 on page 1 and item20 on page 2.
const names = Array.from(
  {length: 21},
  (_, i) => `item${String(i).padStart(2, '0')}`,
);

const nowSeconds = Math.floor(Date.now() / 1000);

const surfaces: [string, string, () => React.ReactElement][] = [
  [
    'AddToRepository',
    '#robot-wizard-repo-search',
    () => (
      <AddToRepository
        namespace="org"
        dropdownItems={[]}
        selectedRepos={[]}
        repos={names.map((name) => ({name, last_modified: 0}) as never)}
        setSelectedRepos={vi.fn()}
        selectedRepoPerms={[]}
        setSelectedRepoPerms={vi.fn()}
        setShowRepoModalSave={vi.fn()}
      />
    ),
  ],
  [
    'TeamView',
    '#robot-wizard-team-search',
    () => (
      <TeamView
        items={names.map((name) => ({name, role: 'member', member_count: 1}))}
        showCheckbox={false}
        showToggleGroup={false}
        filterWithDropdown={false}
      />
    ),
  ],
  [
    'TeamView with dropdown filter',
    '#filter-with-dropdown input',
    () => (
      <TeamView
        items={names.map((name) => ({name, role: 'member', member_count: 1}))}
        showCheckbox={false}
        showToggleGroup={false}
        filterWithDropdown={true}
        dropdownItems={[]}
      />
    ),
  ],
  [
    'SelectOrganization',
    '#gitnamespaces-search-input',
    () => {
      vi.mocked(useGitNamespaces).mockReturnValue({
        gitNamespaces: names.map((name) => ({
          id: name,
          title: name,
          score: 1,
        })),
        isLoading: false,
        isError: false,
      } as never);
      return (
        <SelectOrganization
          org="org"
          repo="repo"
          triggerUuid="uuid"
          gitNamespace={null}
          setGitNamespace={vi.fn()}
          service="github"
        />
      );
    },
  ],
  [
    'HostedRepository',
    '#hostedrepositories-search-input',
    () => {
      vi.mocked(useGitSources).mockReturnValue({
        sources: names.map((name) => ({
          name,
          full_name: name,
          description: '',
          last_updated: nowSeconds,
          has_admin_permissions: true,
        })),
        isLoading: false,
        isError: false,
      } as never);
      return (
        <HostedRepository
          org="org"
          repo="repo"
          triggerUuid="uuid"
          repoUrl={null}
          setRepoUrl={vi.fn()}
          gitNamespace={{id: 'ns', title: 'ns'} as never}
          service="github"
        />
      );
    },
  ],
  [
    'RobotAccounts',
    '#robotaccounts-search-input',
    () => {
      vi.mocked(useAnalyzeBuildTrigger).mockReturnValue({
        analysis: {
          status: 'publicbase',
          is_admin: true,
          message: '',
          robots: names.map((name) => ({name, kind: 'user', can_read: true})),
        },
        isLoading: false,
        isError: false,
        isSuccess: true,
      } as never);
      return (
        <RobotAccounts
          namespace="org"
          repo="repo"
          triggerUuid="uuid"
          buildSource="source"
          contextPath="/"
          dockerfilePath="/Dockerfile"
          isOrganization={true}
          robotAccount={null}
          setRobotAccount={vi.fn()}
          setRobotAccountValid={vi.fn()}
        />
      );
    },
  ],
];

describe.each(surfaces)('%s', (_name, searchInput, renderSurface) => {
  it('resets to page 1 when the search query changes', () => {
    const {container} = render(renderSurface());

    fireEvent.click(screen.getAllByLabelText('Go to next page')[0]);
    expect(screen.getByText('item20')).toBeInTheDocument();

    fireEvent.change(container.querySelector(searchInput), {
      target: {value: 'item00'},
    });

    expect(screen.getByText('item00')).toBeInTheDocument();
  });
});
