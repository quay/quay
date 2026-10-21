import {render, screen, within} from 'src/test-utils';
import {getLogs} from 'src/hooks/UseUsageLogs';
import {UsageLogsTable} from './UsageLogsTable';

vi.mock('src/hooks/UseUsageLogs', () => ({
  getLogs: vi.fn(),
}));

vi.mock('src/hooks/UseLogDescriptions', () => ({
  useLogDescriptions: () => ({
    create_repo: () => 'Created repository',
    set_repo_description: (metadata) => metadata.description,
  }),
}));

const log = {
  datetime: '2024-01-02T03:04:05.000Z',
  kind: 'create_repo',
  metadata: {
    namespace: 'example-org',
    repo: 'example-repository',
    performer: 'metadata-user',
  },
  namespace: {name: 'example-org'},
  performer: {name: 'example-user'},
  ip: '192.0.2.1',
};

function renderTable(
  props: Partial<React.ComponentProps<typeof UsageLogsTable>> = {},
  logs = [log],
) {
  vi.mocked(getLogs).mockResolvedValue({logs, nextPage: undefined});

  return render(
    <UsageLogsTable
      starttime="2024-01-01T00:00:00.000Z"
      endtime="2024-01-03T00:00:00.000Z"
      org="example-org"
      repo=""
      type="table"
      {...props}
    />,
  );
}

describe('UsageLogsTable', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders all superuser columns with complete, labeled values', async () => {
    renderTable({isSuperuser: true});

    const table = await screen.findByTestId('usage-logs-table');
    expect(table).toHaveStyle({tableLayout: 'fixed', width: '100%'});
    const headers = within(table).getAllByRole('columnheader');
    expect(headers.map((header) => header.textContent)).toEqual([
      'Date & Time',
      'Description',
      'Namespace',
      'Repository',
      'Performed by',
      'IP Address',
    ]);
    headers.forEach((header) => {
      expect(header).toHaveClass('pf-m-wrap');
    });

    const row = within(table).getAllByRole('row')[1];
    const cells = within(row).getAllByRole('cell');
    const expectedTimestamp = new Date(log.datetime).toLocaleString();
    expect(cells).toHaveLength(6);
    expect(cells[0]).toHaveTextContent(expectedTimestamp);
    expect(cells[0].querySelector('.pf-m-truncate')).toBeNull();
    expect(cells[1]).toHaveClass('pf-m-break-word');

    const dataLabels = [
      'Date & Time',
      'Description',
      'Namespace',
      'Repository',
      'Performed by',
      'IP Address',
    ];
    cells.forEach((cell, index) => {
      expect(cell).toHaveAttribute('data-label', dataLabels[index]);
    });
    expect(cells[2]).toHaveTextContent('example-org');
    expect(cells[3]).toHaveTextContent('example-repository');
    expect(cells[4]).toHaveTextContent('example-user');
    expect(cells[5]).toHaveTextContent('192.0.2.1');
  });

  it('uses namespace and repository for organization logs', async () => {
    renderTable();

    const table = await screen.findByTestId('usage-logs-table');
    expect(
      within(table).queryByRole('columnheader', {name: 'Namespace'}),
    ).toBeNull();
    expect(
      within(table).getByRole('columnheader', {name: 'Repository'}),
    ).toBeInTheDocument();
    expect(
      within(table).getByText('example-org/example-repository'),
    ).toBeInTheDocument();
  });

  it('wraps unbroken description values without changing the table layout', async () => {
    const description = `symbols-${'#%&'.repeat(100)}`;
    renderTable({isSuperuser: true}, [
      {
        ...log,
        kind: 'set_repo_description',
        metadata: {...log.metadata, description},
      },
    ]);

    const table = await screen.findByTestId('usage-logs-table');
    const descriptionCell = within(table).getByText(description);
    expect(table).toHaveStyle({tableLayout: 'fixed', width: '100%'});
    expect(descriptionCell.closest('td')).toHaveClass('pf-m-break-word');
  });

  it('omits the repository column for repository logs', async () => {
    renderTable({repo: 'example-repository'});

    const table = await screen.findByTestId('usage-logs-table');
    expect(
      within(table).queryByRole('columnheader', {name: 'Repository'}),
    ).toBeNull();
    expect(
      within(table).queryByText('example-org/example-repository'),
    ).toBeNull();
  });
});
