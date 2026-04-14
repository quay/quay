import React from 'react';
import {render, screen} from '@testing-library/react';
import {UsageLogsTable} from '../UsageLogsTable';
import {useInfiniteQuery} from '@tanstack/react-query';

jest.mock('@tanstack/react-query', () => ({
  useInfiniteQuery: jest.fn(),
}));

jest.mock('src/hooks/UseUsageLogs', () => ({
  getLogs: jest.fn(),
}));

jest.mock('src/hooks/UseLogDescriptions', () => ({
  useLogDescriptions: () => ({}),
}));

jest.mock('src/hooks/usePaginatedSortableTable', () => ({
  usePaginatedSortableTable: (data: any[]) => ({
    paginatedData: data,
    getSortableSort: () => undefined,
    paginationProps: {
      total: data.length,
      itemsList: data,
      perPage: 20,
      page: 1,
      setPage: jest.fn(),
      setPerPage: jest.fn(),
    },
  }),
}));

jest.mock('src/components/toolbar/ToolbarPagination', () => ({
  ToolbarPagination: () => <div data-testid="toolbar-pagination" />,
}));

const mockUseInfiniteQuery = useInfiniteQuery as jest.Mock;

const mockLog = {
  datetime: '2026-04-14T10:00:00Z',
  kind: 'push_repo',
  metadata: {namespace: 'myorg', repo: 'myimage', performer: 'user1'},
  performer: {name: 'user1'},
  ip: '127.0.0.1',
};

const mockQueryResult = {
  data: {pages: [{logs: [mockLog]}]},
  isLoading: false,
  isError: false,
  error: null,
  fetchNextPage: jest.fn(),
  hasNextPage: false,
  isFetchingNextPage: false,
};

beforeEach(() => {
  mockUseInfiniteQuery.mockReturnValue(mockQueryResult);
});

afterEach(() => {
  jest.clearAllMocks();
});

describe('UsageLogsTable — Repository column display', () => {
  it('superuser mode: Repository column shows only repo name without namespace prefix', () => {
    render(
      <UsageLogsTable
        starttime="2026-04-01"
        endtime="2026-04-14"
        org="myorg"
        repo=""
        type="org"
        isSuperuser={true}
      />,
    );

    // Should show only the repo name
    expect(screen.getByText('myimage')).toBeInTheDocument();
    // Should NOT show namespace/repo combined
    expect(screen.queryByText('myorg/myimage')).not.toBeInTheDocument();
  });

  it('non-superuser mode: Repository column shows full namespace/repo format', () => {
    render(
      <UsageLogsTable
        starttime="2026-04-01"
        endtime="2026-04-14"
        org="myorg"
        repo=""
        type="org"
        isSuperuser={false}
      />,
    );

    // Should show the full namespace/repo
    expect(screen.getByText('myorg/myimage')).toBeInTheDocument();
  });

  it('no repo metadata: Repository column shows empty string', () => {
    const logWithNoRepo = {
      ...mockLog,
      metadata: {namespace: 'myorg', performer: 'user1'},
    };
    mockUseInfiniteQuery.mockReturnValue({
      ...mockQueryResult,
      data: {pages: [{logs: [logWithNoRepo]}]},
    });

    render(
      <UsageLogsTable
        starttime="2026-04-01"
        endtime="2026-04-14"
        org="myorg"
        repo=""
        type="org"
        isSuperuser={true}
      />,
    );

    // Should not show namespace/repo or just repo
    expect(screen.queryByText('myorg/myimage')).not.toBeInTheDocument();
    expect(screen.queryByText('myimage')).not.toBeInTheDocument();
  });
});
