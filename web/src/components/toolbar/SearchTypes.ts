export interface SearchState {
  query: string;
  field: string;
  isRegEx?: boolean;
}

export interface OrgSearchState extends SearchState {
  currentOrganization: string;
}
