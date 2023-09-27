import {Select, SelectOption, SelectVariant} from '@patternfly/react-core';
import {useEffect, useState} from 'react';
import {useEntities} from 'src/hooks/UseEntities';
import {Entity, getMemberType} from 'src/resources/UserResource';

export default function EntitySearch(props: EntitySearchProps) {
  const [selectedEntityName, setSelectedEntityName] = useState<string>();
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const {entities, isError, searchTerm, setSearchTerm} = useEntities(
    props.org,
    props?.includeTeams,
  );

  useEffect(() => {
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

  useEffect(() => {
    if (props?.value !== null && props?.value !== undefined) {
      setSearchTerm(props.value);
      setSelectedEntityName(props.value);
    }
  }, [props?.value]);

  useEffect(() => {
    if (isError) {
      props.onError();
    }
  }, [isError]);

  return (
    <Select
      toggleId={props.id ? props.id : 'entity-search'}
      isOpen={isOpen}
      selections={searchTerm}
      onSelect={(e, value, isPlaceholder) => {
        // Handles the case when the selected option is an action item. The
        // handler is defined within the child option component
        if (!isPlaceholder) {
          setSearchTerm(value as string);
          setSelectedEntityName(value as string);
        }
        setIsOpen(!isOpen);
      }}
      onToggle={() => {
        setIsOpen(!isOpen);
      }}
      variant={SelectVariant.typeahead}
      onTypeaheadInputChanged={(value) => {
        setSearchTerm(value);
      }}
      shouldResetOnSelect={true}
      onClear={() => {
        props?.onClear({});
        setSearchTerm('');
      }}
      placeholderText={props.placeholderText}
    >
      <></>
      {!searchTerm
        ? props?.defaultOptions
        : entities?.map((e) => (
            <SelectOption
              key={e.name}
              value={e.name}
              description={getMemberType(e)}
            />
          ))}
    </Select>
  );
}

interface EntitySearchProps {
  org: string;
  includeTeams?: boolean;
  onSelect: (selectedItem: Entity) => void;
  onClear?: (entity: any) => void;
  onError?: () => void;
  id?: string;
  defaultOptions?: any;
  defaultSelection?: string;
  placeholderText?: string;
  value?: string;
}
