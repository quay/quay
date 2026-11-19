import {render, screen, userEvent, within} from 'src/test-utils';
import {MemoryRouter} from 'react-router-dom';
import Build from './Build';

vi.mock('src/hooks/UseQuayConfig', () => ({
  useQuayConfig: () => ({config: {SERVER_HOSTNAME: 'localhost:8080'}}),
}));

vi.mock('src/hooks/UseRepository', () => ({
  useRepository: () => ({
    repoDetails: {can_write: true, can_admin: true},
    isLoading: false,
    isError: false,
    errorLoadingRepoDetails: null,
  }),
}));

vi.mock('src/hooks/UseBuilds', () => ({
  useBuild: () => ({
    build: {
      id: 'build-1',
      phase: 'complete',
      started: '2026-11-18T00:00:00Z',
      trigger: null,
      trigger_metadata: null,
    },
    isLoading: false,
    isError: false,
    error: null,
  }),
  useBuildLogs: () => ({
    logs: [
      {
        type: 'phase',
        message: 'building',
        index: 0,
        data: {},
        logs: [{message: 'step output line'}],
      },
    ],
    isLoading: false,
    isError: false,
    error: null,
  }),
  useCancelBuild: () => ({cancelBuild: vi.fn()}),
}));

describe('Build', () => {
  it('renders log headers and expanded container logs with test ids', async () => {
    render(
      <MemoryRouter initialEntries={['/repository/org/repo/build/build-1']}>
        <Build />
      </MemoryRouter>,
    );

    const header = screen.getByTestId('build-log-header');
    expect(screen.queryByTestId('build-container-logs')).toBeNull();

    await userEvent.click(within(header).getByText('building'));

    expect(
      within(screen.getByTestId('build-container-logs')).getByText(
        'step output line',
      ),
    ).toBeInTheDocument();
  });
});
