import {AxiosResponse} from 'axios';
import axios from 'src/libs/axios';
import {assertHttpCode} from './ErrorHandling';
import {IAvatar} from './OrganizationResource';

export interface ISearchResultNamespace {
  title: string;
  kind: string;
  avatar: IAvatar | null;
  name: string;
  score: number;
  href: string;
}

export interface ISearchResult {
  kind: string;
  title: string;
  namespace: ISearchResultNamespace;
  name: string;
  description: string | null;
  is_public: boolean;
  score: number;
  href: string;
  last_modified?: number;
  stars?: number;
  popularity?: number;
}

export interface ISearchResponse {
  results: ISearchResult[];
  has_additional: boolean;
  page: number;
  page_size: number;
  start_index: number;
}

export interface ISearchSuggestion {
  kind: string;
  title: string;
  name: string;
  avatar?: IAvatar | null;
  score: number;
  href: string;
  description?: string | null;
  namespace?: ISearchResultNamespace;
  organization?: ISearchResultNamespace;
}

export interface ISearchSuggestionsResponse {
  results: ISearchSuggestion[];
}

export async function fetchSearchSuggestions(
  query: string,
): Promise<ISearchSuggestionsResponse> {
  const response: AxiosResponse<ISearchSuggestionsResponse> = await axios.get(
    '/api/v1/find/all',
    {
      params: {query},
    },
  );
  assertHttpCode(response.status, 200);
  return response.data;
}

export async function fetchSearchResults(
  query: string,
  page = 1,
): Promise<ISearchResponse> {
  const response: AxiosResponse<ISearchResponse> = await axios.get(
    '/api/v1/find/repositories',
    {
      params: {
        query,
        page,
        includeUsage: true,
      },
    },
  );
  assertHttpCode(response.status, 200);
  return response.data;
}
