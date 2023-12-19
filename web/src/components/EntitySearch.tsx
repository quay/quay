import React from 'react';
import {
  Select,
  SelectOption,
  SelectList,
  MenuToggle,
  MenuToggleElement,
  TextInputGroup,
  TextInputGroupMain,
  TextInputGroupUtilities,
  Button,
} from '@patternfly/react-core';
import TimesIcon from '@patternfly/react-icons/dist/esm/icons/times-icon';
import {useEntities} from 'src/hooks/UseEntities';
import {Entity, getEntityKind} from 'src/resources/UserResource';

export default function EntitySearch(props: EntitySearchProps) {
  const [isOpen, setIsOpen] = React.useState(false);
  const [selectedEntityName, setSelectedEntityName] = React.useState<string>();
  const [focusedItemIndex, setFocusedItemIndex] = React.useState<number | null>(
    null,
  );
  const textInputRef = React.useRef<HTMLInputElement>();
  const {entities, isError, searchTerm, setSearchTerm} = useEntities(
    props.org,
    props?.includeTeams,
  );
  const id = props.id || 'entity-search';

  const onToggleClick = () => setIsOpen(!isOpen);

  React.useEffect(() => {
    if (
      selectedEntityName !== undefined &&
      selectedEntityName !== '' &&
      entities.length > 0
    ) {
      const filteredEntity = entities.filter(
        (e) => e.name === selectedEntityName,
      );
      const selectedEntity =
        filteredEntity.length > 0 ? filteredEntity[0] : null;
      if (selectedEntity !== null && searchTerm !== '') {
        props.onSelect(selectedEntity);
      }
    }
  }, [searchTerm, JSON.stringify(entities)]);

  React.useEffect(() => {
    if (props?.value !== null && props?.value !== undefined) {
      setSearchTerm(props.value);
      setSelectedEntityName(props.value);
    }
  }, [props?.value]);

  React.useEffect(() => {
    if (isError) {
      props.onError();
    }
  }, [isError]);

  const onSelect = (
    _event: React.MouseEvent<Element, MouseEvent> | undefined,
    value: string | number | undefined,
  ) => {
    if (value && value !== 'no results') {
      setSearchTerm(value as string);
      setSelectedEntityName(value as string);
    }
    // onClear() prop can be skipped in case the value needs to be cleared automatically from
    // the dropdown after selection (used in AddTeamMember wizard step)
    if (!props.onClear) {
      setSearchTerm('');
      setSelectedEntityName('');
    }
    setIsOpen(false);
    setFocusedItemIndex(null);
  };

  const onTextInputChange = (
    _event: React.FormEvent<HTMLInputElement>,
    value: string,
  ) => {
    setSearchTerm(value);
  };

  const toggle = (toggleRef: React.Ref<MenuToggleElement>) => (
    <MenuToggle
      ref={toggleRef}
      id={id}
      variant="typeahead"
      onClick={onToggleClick}
      isExpanded={isOpen}
      isFullWidth
    >
      <TextInputGroup isPlain>
        <TextInputGroupMain
          value={searchTerm}
          onClick={onToggleClick}
          onChange={onTextInputChange}
          id={`${id}-input`}
          autoComplete="off"
          innerRef={textInputRef}
          placeholder={props.placeholderText}
          role="combobox"
          isExpanded={isOpen}
          aria-controls="entity-select-listbox"
        />

        <TextInputGroupUtilities>
          {!!searchTerm && (
            <Button
              variant="plain"
              onClick={() => {
                setSelectedEntityName('');
                setSearchTerm('');
                textInputRef?.current?.focus();
                props?.onClear();
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
      id="entity-select"
      isOpen={isOpen}
      selected={searchTerm}
      onSelect={onSelect}
      onOpenChange={() => setIsOpen(false)}
      toggle={toggle}
      shouldFocusToggleOnSelect
    >
      <SelectList id="entity-search-option-list">
        {!searchTerm
          ? props?.defaultOptions
          : entities?.map((entity, index) => (
              <SelectOption
                data-testid={entity.name}
                key={entity.name}
                value={entity.name}
                isFocused={focusedItemIndex === index}
                onClick={() => {
                  setSelectedEntityName(entity.name);
                  if (props?.onSelect) {
                    props.onSelect(entity);
                  }
                }}
                description={getEntityKind(entity)}
              >
                {entity.name}
              </SelectOption>
            ))}
      </SelectList>
    </Select>
  );
}

interface EntitySearchProps {
  org: string;
  includeTeams?: boolean;
  onSelect: (selectedItem: Entity) => void;
  onClear?: () => void;
  onError?: () => void;
  id?: string;
  defaultOptions?: any;
  defaultSelection?: string;
  placeholderText?: string;
  value?: string;
}
