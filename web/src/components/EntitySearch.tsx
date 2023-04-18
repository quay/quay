import {
  Select,
  SelectOption,
  SelectVariant,
  Spinner,
} from '@patternfly/react-core';
import {useEffect, useState} from 'react';
import {useEntities} from 'src/hooks/UseEntities';
import {Entity, getMemberType} from 'src/resources/UserResource';
import EntityIcon from './EntityIcon';

export default function EntitySearch(props: EntitySearchProps) {
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const {entities, isLoadingEntities, isError, searchTerm, setSearchTerm} =
    useEntities(props.org);

  useEffect(() => {
    if (searchTerm != undefined && searchTerm != '') {
      const filteredEntity = entities.filter((e) => e.name === searchTerm);
      const selectedEntity =
        filteredEntity.length > 0 ? filteredEntity[0] : null;
      props.onSelect(selectedEntity);
    } else {
      props.onSelect(null);
    }
  }, [searchTerm, JSON.stringify(entities)]);

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
      onSelect={(e, value) => {
        setSearchTerm(value as string);
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
        setSearchTerm('');
      }}
      loadingVariant={isLoadingEntities ? 'spinner' : undefined}
    >
      {isLoadingEntities
        ? undefined
        : entities.map((e) => (
            <SelectOption key={e.name} value={e.name}>
              <EntityIcon type={getMemberType(e)} includeIcon />
              {e.name}
            </SelectOption>
          ))}
    </Select>
  );
}

interface EntitySearchProps {
  org: string;
  onSelect: (entity: Entity) => void;
  onError?: () => void;
  id?: string;
}
