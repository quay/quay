import {useEffect, useRef, useState} from 'react';
import {useNavigate} from 'react-router-dom';
import {
  Flex,
  FlexItem,
  Popper,
  SearchInput,
  Spinner,
} from '@patternfly/react-core';
import {useSearchSuggestions} from 'src/hooks/UseSearch';
import Avatar from 'src/components/Avatar';
import {generateAvatarFromName} from 'src/libs/avatarUtils';
import {ISearchSuggestion} from 'src/resources/SearchResource';
import 'src/components/header/HeaderSearchBar.css';

const MIN_QUERY_LENGTH = 3;

function getSuggestionLabel(s: ISearchSuggestion) {
  if (s.kind === 'repository' && s.namespace) {
    return `${s.namespace.name}/${s.name}`;
  }
  if (s.kind === 'team' && s.organization) {
    return `${s.organization.name}/${s.name}`;
  }
  return s.name;
}

export default function HeaderSearchBar() {
  const navigate = useNavigate();
  const [inputValue, setInputValue] = useState('');
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);

  const searchBoxRef = useRef<HTMLDivElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  // Set when the user explicitly dismisses the dropdown so a background
  // refetch of suggestions doesn't reopen it behind their back.
  const isDismissedRef = useRef(false);

  const {suggestions, isLoading} = useSearchSuggestions(inputValue);

  useEffect(() => {
    if (isDismissedRef.current) {
      return;
    }
    setIsDropdownOpen(
      inputValue.trim().length >= MIN_QUERY_LENGTH && suggestions.length > 0,
    );
  }, [suggestions, inputValue]);

  useEffect(() => {
    setActiveIndex(-1);
  }, [suggestions]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node;
      if (
        !searchBoxRef.current?.contains(target) &&
        !dropdownRef.current?.contains(target)
      ) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const closeDropdown = () => {
    isDismissedRef.current = true;
    setIsDropdownOpen(false);
  };

  const handleChange = (value: string) => {
    isDismissedRef.current = false;
    setInputValue(value);
  };

  const goToSuggestion = (suggestion: ISearchSuggestion) => {
    closeDropdown();
    setInputValue('');
    navigate(suggestion.href);
  };

  const goToSearchPage = () => {
    const trimmed = inputValue.trim();
    if (trimmed) {
      closeDropdown();
      setInputValue('');
      navigate(`/search?q=${encodeURIComponent(trimmed)}`);
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter') {
      if (isDropdownOpen && activeIndex >= 0 && suggestions[activeIndex]) {
        goToSuggestion(suggestions[activeIndex]);
      } else {
        goToSearchPage();
      }
    }
    if (event.key === 'Escape') {
      closeDropdown();
    }
    if (event.key === 'ArrowDown' && isDropdownOpen && suggestions.length > 0) {
      event.preventDefault();
      setActiveIndex((prev) => (prev < suggestions.length - 1 ? prev + 1 : 0));
    }
    if (event.key === 'ArrowUp' && isDropdownOpen && suggestions.length > 0) {
      event.preventDefault();
      setActiveIndex((prev) => (prev > 0 ? prev - 1 : suggestions.length - 1));
    }
  };

  const searchInput = (
    <div ref={searchBoxRef} className="header-search-input">
      <SearchInput
        value={inputValue}
        placeholder="Search repositories and organizations..."
        onChange={(_event, value) => handleChange(value)}
        onClear={() => {
          setInputValue('');
          closeDropdown();
        }}
        aria-label="Search repositories and organizations"
        // The combobox contract has to live on the focusable <input>, not on
        // the wrapper PatternFly renders around it. `inputProps` is the only
        // prop SearchInput forwards all the way down to the input element.
        inputProps={{
          'data-testid': 'header-search-input',
          role: 'combobox',
          'aria-expanded': isDropdownOpen,
          'aria-controls': 'header-search-suggestions',
          'aria-activedescendant':
            activeIndex >= 0
              ? `header-search-suggestion-${activeIndex}`
              : undefined,
          'aria-autocomplete': 'list',
          onKeyDown: handleKeyDown,
        }}
      />
    </div>
  );

  // Plain listbox markup rather than PatternFly's Menu: MenuItem renders the
  // `id` onto an inner role="menuitem" button, which both breaks the
  // aria-activedescendant reference and nests a menuitem inside a listbox.
  const suggestionsDropdown = (
    <div ref={dropdownRef} className="header-search-dropdown">
      <ul
        id="header-search-suggestions"
        role="listbox"
        aria-label="Search suggestions"
        className="header-search-suggestion-list"
      >
        {suggestions.map((s, i) => (
          <li
            key={`${s.kind}-${s.href}`}
            id={`header-search-suggestion-${i}`}
            role="option"
            aria-selected={i === activeIndex}
            className={`header-search-suggestion${
              i === activeIndex ? ' header-search-suggestion-active' : ''
            }`}
            // Keep focus on the input so aria-activedescendant stays valid.
            onMouseDown={(event) => event.preventDefault()}
            onMouseEnter={() => setActiveIndex(i)}
            onClick={() => goToSuggestion(s)}
          >
            <Flex
              alignItems={{default: 'alignItemsCenter'}}
              spaceItems={{default: 'spaceItemsSm'}}
              flexWrap={{default: 'nowrap'}}
            >
              <FlexItem>
                <span className="header-search-suggestion-kind">
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
          </li>
        ))}
      </ul>
    </div>
  );

  return (
    <div className="header-search-container">
      <Popper
        trigger={searchInput}
        popper={suggestionsDropdown}
        isVisible={isDropdownOpen}
        enableFlip={false}
        minWidth="trigger"
        // Rendered into the body rather than the masthead so the dropdown is
        // not clipped by the header's stacking/overflow context.
        appendTo={() => document.body}
      />
      {isLoading && inputValue.trim().length >= MIN_QUERY_LENGTH && (
        <Spinner size="sm" className="header-search-spinner" />
      )}
    </div>
  );
}
