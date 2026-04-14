import React from 'react';
import {render, screen} from '@testing-library/react';
import {UsageLogsTable} from '../UsageLogsTable';

jest.mock('@tanstack/react-query', () => ({
  useInfiniteQuery: jest.fn(),
}));
jest.mock('src/hooks/UseUsageLogs', () => ({getLogs: jest.fn()}));
jest.mock('src/hooks/UseLogDescriptions', () => ({
  useLogDescriptions: () => ({}),
}));
jest.mock('src/hooks/usePaginatedSortableTable', () => ({
  usePaginatedSortableTable: (data: any[]) => ({
    paginatedData: data,
    getSortableSort: () => undefined,
    paginationProps: {
      itemCount: data.length,
      perPage: 20,
      page: 1,
      onSetPage: jest.fn(),
      onPerPageSelect: jest.fn(),
    },
  }),
}));

import {useInfiniteQuery} from '@tanstack/react-query';
const mockUseInfiniteQuery = useInfiniteQuery as jest.Mock;

const baseQueryReturn = {
  data: {pages: [{logs: []}]},
  isLoading: false,
  isError: false,
  fetchNextPage: jest.fn(),
  hasNextPage: false,
  isFetchingNextPage: false,
};

const defaultProps = {
  starttime: '2026-04-01',
  endtime: '2026-04-14',
  org: 'myorg',
  repo: '',
  type: 'org',
};

// jsdom does not implement IntersectionObserver — provide a no-op stub
const mockIntersectionObserver = jest.fn(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));

describe('UsageLogsTable — Load More footer', () => {
  beforeEach(() => {
    mockUseInfiniteQuery.mockReturnValue({...baseQueryReturn});
    window.IntersectionObserver = mockIntersectionObserver as any;
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('shows spinner when isFetchingNextPage is true and hasNextPage is true', () => {
    mockUseInfiniteQuery.mockReturnValue({
      ...baseQueryReturn,
      hasNextPage: true,
      isFetchingNextPage: true,
    });

    render(<UsageLogsTable {...defaultProps} />);

    expect(screen.getByTestId('load-more-spinner')).toBeInTheDocument();
    expect(screen.queryByTestId('load-more-button')).not.toBeInTheDocument();
  });

  it('shows spinner when isFetchingNextPage is true even if hasNextPage is false', () => {
    mockUseInfiniteQuery.mockReturnValue({
      ...baseQueryReturn,
      hasNextPage: false,
      isFetchingNextPage: true,
    });

    render(<UsageLogsTable {...defaultProps} />);

    expect(screen.getByTestId('load-more-spinner')).toBeInTheDocument();
    expect(screen.queryByTestId('load-more-button')).not.toBeInTheDocument();
  });

  it('shows Load More button when hasNextPage is true and not fetching', () => {
    mockUseInfiniteQuery.mockReturnValue({
      ...baseQueryReturn,
      hasNextPage: true,
      isFetchingNextPage: false,
    });

    render(<UsageLogsTable {...defaultProps} />);

    expect(screen.getByTestId('load-more-button')).toBeInTheDocument();
    expect(screen.queryByTestId('load-more-spinner')).not.toBeInTheDocument();
  });

  it('shows nothing when hasNextPage is false and not fetching', () => {
    mockUseInfiniteQuery.mockReturnValue({
      ...baseQueryReturn,
      hasNextPage: false,
      isFetchingNextPage: false,
    });

    render(<UsageLogsTable {...defaultProps} />);

    expect(screen.queryByTestId('load-more-button')).not.toBeInTheDocument();
    expect(screen.queryByTestId('load-more-spinner')).not.toBeInTheDocument();
  });
});
