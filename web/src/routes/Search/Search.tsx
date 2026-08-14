import {useCallback, useEffect, useMemo, useRef, useState} from 'react';
import {Link, useNavigate, useSearchParams} from 'react-router-dom';
import {
  Button,
  EmptyState,
  EmptyStateBody,
  Flex,
  FlexItem,
  Menu,
  MenuContent,
  MenuItem,
  MenuList,
  PageSection,
  Popper,
  Spinner,
  TextInputGroup,
  TextInputGroupMain,
  TextInputGroupUtilities,
  Title,
  Pagination,
  PaginationVariant,
  Toolbar,
  ToolbarContent,
  ToolbarItem,
} from '@patternfly/react-core';
import {StarIcon, SearchIcon, TimesIcon} from '@patternfly/react-icons';
import {useSearch, useSearchSuggestions} from 'src/hooks/UseSearch';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import Avatar from 'src/components/Avatar';
import {generateAvatarFromName} from 'src/libs/avatarUtils';
import {formatRelativeTime} from 'src/libs/utils';
import RequestError from 'src/components/errors/RequestError';
import {ISearchResult, ISearchSuggestion} from 'src/resources/SearchResource';
import './Search.css';

export default function Search() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const query = searchParams.get('q') || '';
  const parsedPage = parseInt(searchParams.get('page') || '1', 10);
  const page = Number.isFinite(parsedPage) && parsedPage > 0 ? parsedPage : 1;

  const [inputValue, setInputValue] = useState(query);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);

  const inputRef = useRef<HTMLInputElement>(null);
  const searchBoxRef = useRef<HTMLDivElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const quayConfig = useQuayConfig();
  const maxPageCount = quayConfig?.config?.SEARCH_MAX_RESULT_PAGE_COUNT ?? 10;

  const {results, hasAdditional, pageSize, startIndex, isLoading, error} =
    useSearch(query, page);
  const {suggestions} = useSearchSuggestions(inputValue);

  const rawTotal = hasAdditional
    ? (page + 1) * pageSize
    : startIndex + results.length;
  const effectiveTotal = Math.min(rawTotal, maxPageCount * pageSize);

  useEffect(() => {
    setInputValue(query);
  }, [query]);

  useEffect(() => {
    const isTyping = inputValue.trim() !== query;
    setIsDropdownOpen(
      isTyping && inputValue.trim().length >= 3 && suggestions.length > 0,
    );
  }, [suggestions, inputValue, query]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node;
      if (
        searchBoxRef.current &&
        !searchBoxRef.current.contains(target) &&
        dropdownRef.current &&
        !dropdownRef.current.contains(target)
      ) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSearch = useCallback(() => {
    const trimmed = inputValue.trim();
    if (trimmed) {
      setIsDropdownOpen(false);
      setSearchParams({q: trimmed, page: '1'});
    }
  }, [inputValue, setSearchParams]);

  const handleClear = () => {
    setInputValue('');
    setIsDropdownOpen(false);
    setSearchParams({});
    inputRef.current?.focus();
  };

  const handleInputChange = (_event: React.FormEvent, value: string) => {
    setInputValue(value);
  };

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter') {
      handleSearch();
    }
    if (event.key === 'Escape') {
      setIsDropdownOpen(false);
    }
  };

  const handleSuggestionSelect = (suggestion: ISearchSuggestion) => {
    setIsDropdownOpen(false);
    navigate(suggestion.href);
  };

  const handleSetPage = (_event: unknown, newPage: number) => {
    const params: Record<string, string> = {page: String(newPage)};
    if (query) {
      params.q = query;
    }
    setSearchParams(params);
  };

  const maxPopularity = useMemo(
    () => Math.max(...results.map((r) => r.popularity ?? 0), 1),
    [results],
  );

  const getSuggestionLabel = (s: ISearchSuggestion) => {
    if (s.kind === 'repository' && s.namespace) {
      return `${s.namespace.name}/${s.name}`;
    }
    if (s.kind === 'team' && s.organization) {
      return `${s.organization.name}/${s.name}`;
    }
    return s.name;
  };

  const searchInput = (
    <div ref={searchBoxRef}>
      <TextInputGroup>
        <TextInputGroupMain
          icon={<SearchIcon />}
          value={inputValue}
          placeholder="Search repositories..."
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          ref={inputRef}
          data-testid="search-input"
        />
        <TextInputGroupUtilities>
          {inputValue && (
            <Button
              variant="plain"
              onClick={handleClear}
              aria-label="Clear search"
            >
              <TimesIcon />
            </Button>
          )}
          <Button variant="control" onClick={handleSearch}>
            Search
          </Button>
        </TextInputGroupUtilities>
      </TextInputGroup>
    </div>
  );

  const suggestionsDropdown = (
    <div ref={dropdownRef}>
      <Menu onSelect={() => setIsDropdownOpen(false)}>
        <MenuContent>
          <MenuList>
            {suggestions.map((s, i) => (
              <MenuItem
                key={`${s.kind}-${s.name}-${i}`}
                onClick={() => handleSuggestionSelect(s)}
              >
                <Flex
                  alignItems={{default: 'alignItemsCenter'}}
                  spaceItems={{default: 'spaceItemsSm'}}
                >
                  <FlexItem>
                    <span className="search-suggestion-kind">
                      {s.title || s.kind}
                    </span>
                  </FlexItem>
                  <FlexItem>
                    <Avatar
                      avatar={
                        s.avatar ??
                        (s.namespace?.avatar || generateAvatarFromName(s.name))
                      }
                      size="sm"
                    />
                  </FlexItem>
                  <FlexItem>{getSuggestionLabel(s)}</FlexItem>
                </Flex>
                {s.description && s.kind === 'repository' && (
                  <div className="search-suggestion-description">
                    {s.description.split('\n')[0]}
                  </div>
                )}
              </MenuItem>
            ))}
          </MenuList>
        </MenuContent>
      </Menu>
    </div>
  );

  return (
    <>
      <PageSection hasBodyWrapper={false} hasShadowBottom>
        <Title headingLevel="h1">Search</Title>
      </PageSection>
      <PageSection hasBodyWrapper={false}>
        <div className="search-bar-container">
          <div className="search-toolbar-input">
            <Popper
              trigger={searchInput}
              popper={suggestionsDropdown}
              isVisible={isDropdownOpen}
              enableFlip={false}
              appendTo={() => searchBoxRef.current ?? document.body}
            />
          </div>
        </div>
        {!isLoading && !error && results.length > 0 && (
          <Toolbar>
            <ToolbarContent>
              <ToolbarItem variant="pagination">
                <Pagination
                  itemCount={effectiveTotal}
                  perPage={pageSize}
                  page={page}
                  onSetPage={handleSetPage}
                  perPageOptions={[]}
                  isCompact
                />
              </ToolbarItem>
            </ToolbarContent>
          </Toolbar>
        )}

        {isLoading && (
          <Flex justifyContent={{default: 'justifyContentCenter'}}>
            <Spinner size="lg" />
          </Flex>
        )}

        {error && <RequestError message="Could not load search results" />}

        {!isLoading && !error && results.length === 0 && (
          <EmptyState
            headingLevel="h2"
            icon={SearchIcon}
            titleText="No matching repositories found"
            variant="lg"
          >
            <EmptyStateBody>Please try changing your query.</EmptyStateBody>
          </EmptyState>
        )}

        {!isLoading && !error && results.length > 0 && (
          <>
            <ol className="search-results-list">
              {results.map((result) => (
                <SearchResultItem
                  key={`${result.namespace.name}/${result.name}`}
                  result={result}
                  maxPopularity={maxPopularity}
                />
              ))}
            </ol>

            <Toolbar>
              <ToolbarContent>
                <ToolbarItem variant="pagination">
                  <Pagination
                    itemCount={effectiveTotal}
                    perPage={pageSize}
                    page={page}
                    onSetPage={handleSetPage}
                    perPageOptions={[]}
                    variant={PaginationVariant.bottom}
                  />
                </ToolbarItem>
              </ToolbarContent>
            </Toolbar>

            {page >= maxPageCount && (
              <div className="search-page-navigation">
                <span className="search-max-results-help">
                  You&apos;ve reached the maximum number of viewable results.
                  Please refine your search.
                </span>
              </div>
            )}
          </>
        )}
      </PageSection>
    </>
  );
}

function SearchResultItem({
  result,
  maxPopularity,
}: {
  result: ISearchResult;
  maxPopularity: number;
}) {
  const activityLevel = result.popularity
    ? Math.ceil(
        (Math.log10(result.popularity + 1) / Math.log10(maxPopularity + 1)) * 5,
      )
    : 0;

  return (
    <li className="search-result-item">
      <Flex
        alignItems={{default: 'alignItemsCenter'}}
        spaceItems={{default: 'spaceItemsSm'}}
      >
        <FlexItem>
          <Avatar
            avatar={
              result.namespace.avatar ??
              generateAvatarFromName(result.namespace.name)
            }
            size="sm"
          />
        </FlexItem>
        <FlexItem grow={{default: 'grow'}}>
          <Link to={result.href} className="search-result-repo-name">
            {result.namespace.name}/{result.name}
          </Link>
        </FlexItem>
        <FlexItem align={{default: 'alignRight'}}>
          <span className="search-result-star-count">
            <span>{result.stars ?? 0}</span>
            <StarIcon />
          </span>
        </FlexItem>
      </Flex>

      {result.description && (
        <p className="search-result-description">
          {result.description.split('\n')[0]}
        </p>
      )}

      <div className="search-result-metadata">
        <Flex spaceItems={{default: 'spaceItemsLg'}}>
          <FlexItem grow={{default: 'grow'}}>
            Last Modified:{' '}
            {result.last_modified
              ? formatRelativeTime(result.last_modified)
              : 'Never'}
          </FlexItem>
          <FlexItem align={{default: 'alignRight'}}>
            <span className="search-result-activity">
              activity{' '}
              <span className="search-signal-strength">
                {[1, 2, 3, 4, 5].map((bar) => (
                  <span
                    key={bar}
                    className={`search-signal-bar ${
                      bar <= activityLevel ? 'search-signal-bar-active' : ''
                    }`}
                    style={{height: `${bar * 3}px`}}
                  />
                ))}
              </span>
            </span>
          </FlexItem>
        </Flex>
      </div>
    </li>
  );
}
