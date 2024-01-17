import {
  Ref,
  useEffect,
  useRef,
  useState,
  FormEvent,
  KeyboardEvent,
} from 'react';
import {
  Select,
  SelectOption,
  SelectList,
  SelectOptionProps,
  MenuToggle,
  MenuToggleElement,
  TextInputGroup,
  TextInputGroupMain,
  TextInputGroupUtilities,
  Button,
} from '@patternfly/react-core';
import TimesIcon from '@patternfly/react-icons/dist/esm/icons/times-icon';

// From the Patternfly example
export default function TypeAheadSelect(props: TypeAheadSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [selected, setSelected] = useState<string>('');
  const [filterValue, setFilterValue] = useState<string>('');
  const [selectOptions, setSelectOptions] = useState<SelectOptionProps[]>(
    props.initialSelectOptions,
  );
  const [focusedItemIndex, setFocusedItemIndex] = useState<number | null>(null);
  const [activeItem, setActiveItem] = useState<string | null>(null);
  const textInputRef = useRef<HTMLInputElement>();

  useEffect(() => {
    let newSelectOptions: SelectOptionProps[] = props.initialSelectOptions;

    if (filterValue) {
      newSelectOptions = props.initialSelectOptions.filter((menuItem) =>
        menuItem.value.toLowerCase().includes(filterValue.toLowerCase()),
      );

      if (!newSelectOptions.length) {
        newSelectOptions = [
          {
            isDisabled: false,
            children: `No results found for "${filterValue}"`,
            value: 'no results',
          },
        ];
      }

      if (!isOpen) {
        setIsOpen(true);
      }
    }

    setSelectOptions(newSelectOptions);
    setActiveItem(null);
    setFocusedItemIndex(null);
  }, [filterValue]);

  const onToggleClick = () => {
    setIsOpen(!isOpen);
  };

  const onSelect = (_, value?: string | number) => {
    if (value && value !== 'no results') {
      props.onChange(value as string);
      setFilterValue('');
      setSelected(value as string);
    }
    setIsOpen(false);
    setFocusedItemIndex(null);
    setActiveItem(null);
  };

  const onTextInputChange = (
    _event: FormEvent<HTMLInputElement>,
    value: string,
  ) => {
    props.onChange(value);
    setFilterValue(value);
  };

  const handleMenuArrowKeys = (key: string) => {
    let indexToFocus;

    if (isOpen) {
      if (key === 'ArrowUp') {
        if (focusedItemIndex === null || focusedItemIndex === 0) {
          indexToFocus = selectOptions.length - 1;
        } else {
          indexToFocus = focusedItemIndex - 1;
        }
      }

      if (key === 'ArrowDown') {
        if (
          focusedItemIndex === null ||
          focusedItemIndex === selectOptions.length - 1
        ) {
          indexToFocus = 0;
        } else {
          indexToFocus = focusedItemIndex + 1;
        }
      }

      setFocusedItemIndex(indexToFocus);
      const focusedItem = selectOptions.filter((option) => !option.isDisabled)[
        indexToFocus
      ];
      setActiveItem(`select-typeahead-${focusedItem.value.replace(' ', '-')}`);
    }
  };

  const onInputKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    const enabledMenuItems = selectOptions.filter(
      (option) => !option.isDisabled,
    );
    const [firstMenuItem] = enabledMenuItems;
    const focusedItem = focusedItemIndex
      ? enabledMenuItems[focusedItemIndex]
      : firstMenuItem;

    switch (event.key) {
      case 'Enter':
        if (isOpen && focusedItem.value !== 'no results') {
          props.onChange(String(focusedItem.children));
          setFilterValue('');
          setSelected(String(focusedItem.children));
        }

        setIsOpen((prevIsOpen) => !prevIsOpen);
        setFocusedItemIndex(null);
        setActiveItem(null);

        break;
      case 'Tab':
      case 'Escape':
        setIsOpen(false);
        setActiveItem(null);
        break;
      case 'ArrowUp':
      case 'ArrowDown':
        event.preventDefault();
        handleMenuArrowKeys(event.key);
        break;
    }
  };

  const toggle = (toggleRef: Ref<MenuToggleElement>) => (
    <MenuToggle
      id="typeahead-select-dropdown"
      ref={toggleRef}
      variant="typeahead"
      onClick={onToggleClick}
      isExpanded={isOpen}
      isFullWidth
    >
      <TextInputGroup isPlain>
        <TextInputGroupMain
          value={props.value}
          onClick={onToggleClick}
          onChange={onTextInputChange}
          onKeyDown={onInputKeyDown}
          id="typeahead-select-input"
          autoComplete="off"
          innerRef={textInputRef}
          placeholder={props.placeholder}
          {...(activeItem && {'aria-activedescendant': activeItem})}
          role="combobox"
          isExpanded={isOpen}
          aria-controls="select-typeahead-listbox"
        />

        <TextInputGroupUtilities>
          {!!props.value && (
            <Button
              variant="plain"
              onClick={() => {
                setSelected('');
                props.onChange('');
                setFilterValue('');
                textInputRef?.current?.focus();
              }}
              aria-label="Clear input value"
            >
              <TimesIcon aria-hidden />
            </Button>
          )}
        </TextInputGroupUtilities>
      </TextInputGroup>
    </MenuToggle>
  );

  return (
    <Select
      id="typeahead-select"
      isOpen={isOpen}
      selected={selected}
      onSelect={onSelect}
      onOpenChange={() => {
        setIsOpen(false);
      }}
      toggle={toggle}
    >
      <SelectList id="select-typeahead-listbox">
        {selectOptions.map((option, index) => (
          <SelectOption
            key={option.value || option.children}
            isFocused={focusedItemIndex === index}
            className={option.className}
            onClick={() => setSelected(option.value)}
            id={`select-typeahead-${option.value.replace(' ', '-')}`}
            {...option}
            ref={null}
          >
            {option.value}
          </SelectOption>
        ))}
      </SelectList>
    </Select>
  );
}

interface TypeAheadSelectProps {
  initialSelectOptions: SelectOptionProps[];
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}
