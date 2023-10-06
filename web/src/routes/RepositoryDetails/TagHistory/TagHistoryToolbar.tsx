import {
  Checkbox,
  SearchInput,
  Toolbar,
  ToolbarContent,
  ToolbarItem,
} from '@patternfly/react-core';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';
import DateTimePicker from 'src/components/DateTimePicker';

export default function TagHistoryToolBar(props: TagHistoryToolBarProps) {
  const {
    showFuture,
    setShowFuture,
    query,
    setQuery,
    startTime,
    setStartTime,
    endTime,
    setEndTime,
    page,
    setPage,
    perPage,
    setPerPage,
    total,
  } = props;
  return (
    <Toolbar>
      <ToolbarContent alignItems="center">
        <ToolbarItem variant="search-filter">
          <SearchInput
            placeholder="Search by tag name..."
            value={query}
            onChange={(_, value) => {
              setQuery(value);
            }}
            onClear={() => {
              setQuery('');
            }}
          />
        </ToolbarItem>
        <ToolbarItem alignItems="center">
          Date range:
          <DateTimePicker
            id="start-time-picker"
            value={startTime}
            setValue={setStartTime}
          />
          to
          <DateTimePicker
            id="end-time-picker"
            value={endTime}
            setValue={setEndTime}
          />
        </ToolbarItem>
        <ToolbarItem alignSelf="center">
          <Checkbox
            label="Show future"
            id="show-future-checkbox"
            isChecked={showFuture}
            onChange={() => {
              setShowFuture(!showFuture);
            }}
          />
        </ToolbarItem>
        <ToolbarPagination
          total={total}
          perPage={perPage}
          page={page}
          setPage={setPage}
          setPerPage={setPerPage}
          isCompact
        />
      </ToolbarContent>
    </Toolbar>
  );
}

interface TagHistoryToolBarProps {
  showFuture: boolean;
  setShowFuture: (showFuture: boolean) => void;
  query: string;
  setQuery: (query: string) => void;
  startTime: Date;
  setStartTime: (set: (prev: Date) => Date) => void;
  endTime: Date;
  setEndTime: (set: (prev: Date) => Date) => void;
  page: number;
  setPage: (page: number) => void;
  perPage: number;
  setPerPage: (perPage: number) => void;
  total: number;
}
