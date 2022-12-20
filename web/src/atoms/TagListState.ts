import {atom, selector} from 'recoil';
import {SearchState} from 'src/components/toolbar/SearchTypes';
import {Tag} from 'src/resources/TagResource';
import ColumnNames from 'src/routes/RepositoryDetails/Tags/ColumnNames';

export const searchTagsState = atom<SearchState>({
  key: 'searchsearchTagsStateState',
  default: {
    query: '',
    field: ColumnNames.name,
  },
});

export const searchTagsFilterState = selector({
  key: 'searchFilter',
  get: ({get}) => {
    const search = get(searchTagsState);
    if (search.query === '') {
      return null;
    }

    const filterByName = (tag: Tag) => tag.name.includes(search.query);
    const filterByDigest = (tag: Tag) =>
      tag.manifest_digest.includes(search.query);

    switch (search.field) {
      case ColumnNames.manifest:
        return filterByDigest;
      case ColumnNames.name:
      default:
        return filterByName;
    }
  },
});

export const paginationState = atom({
  key: 'paginationState',
  default: {
    page: 1,
    perPage: 25,
  },
});

export const selectedTagsState = atom({
  key: 'selectedTagsState',
  default: [],
});

export const currentOpenPopoverState = atom({
  key: 'currentOpenPopoverState',
  default: '',
});
