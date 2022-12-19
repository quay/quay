import {
  Pagination,
  ToolbarItem,
  PaginationVariant,
} from '@patternfly/react-core';

export const ToolbarPagination = (props: ToolbarPaginationProps) => {
  return (
    <ToolbarItem variant="pagination">
      <Pagination
        perPageComponent="button"
        itemCount={props.total || props.itemsList.length}
        perPage={props.perPage}
        id={props.id ? props.id : 'toolbar-pagination'}
        page={props.page}
        onSetPage={(_event, pageNumber) => props.setPage(pageNumber)}
        onPerPageSelect={(_event, perPageNumber) => {
          props.setPage(1);
          props.setPerPage(perPageNumber);
        }}
        widgetId="pagination-options-menu-top"
        variant={
          props.bottom ? PaginationVariant.bottom : PaginationVariant.top
        }
      />
    </ToolbarItem>
  );
};

type ToolbarPaginationProps = {
  itemsList: any[];
  perPage: number;
  page: number;
  setPage: (pageNumber: number) => void;
  setPerPage: (perPageNumber: number) => void;
  bottom?: boolean;
  id?: string;
  total?: number;
};
