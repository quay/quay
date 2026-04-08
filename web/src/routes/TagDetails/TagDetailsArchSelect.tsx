import React from 'react';
import {
  Flex,
  FlexItem,
  Label,
  MenuToggle,
  MenuToggleElement,
  SelectList,
} from '@patternfly/react-core';
import {Select, SelectOption} from '@patternfly/react-core';
import {Manifest} from 'src/resources/TagResource';

export default function ArchSelect(props: ArchSelectProps) {
  const [isOpen, setIsOpen] = React.useState(false);

  const onSelect = (
    _event: React.MouseEvent<Element, MouseEvent> | undefined,
    value: string | number | undefined,
  ) => {
    // Prevent selecting missing architectures
    const selectedManifest = props.options.find((m) => m.digest === value);
    if (selectedManifest?.is_present === false) {
      return;
    }
    props.setDigest(value as string);
    setIsOpen(false);
  };

  if (!props.render) return null;

  return (
    <Flex style={props.style ? props.style : undefined}>
      <FlexItem>Architecture</FlexItem>
      <FlexItem>
        <Select
          data-testid="arch-select"
          aria-label="Architecture select"
          isOpen={isOpen}
          selected={props.digest || 'Architecture'}
          onSelect={onSelect}
          onOpenChange={(isOpen) => setIsOpen(isOpen)}
          toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
            <MenuToggle
              ref={toggleRef}
              onClick={() => setIsOpen(() => !isOpen)}
              isExpanded={isOpen}
            >
              {getPlatformValue(
                props.options.find((option) => option.digest === props.digest),
              )}
            </MenuToggle>
          )}
          shouldFocusToggleOnSelect
        >
          <SelectList>
            {props.options.map((manifest, index) => {
              const isMissing = manifest.is_present === false;
              return (
                <SelectOption
                  key={index}
                  value={manifest.digest}
                  isDisabled={isMissing}
                  data-testid={
                    isMissing ? 'missing-arch-option' : 'arch-option'
                  }
                >
                  {getPlatformValue(manifest)}
                  {isMissing && (
                    <Label color="grey" isCompact style={{marginLeft: '8px'}}>
                      Missing
                    </Label>
                  )}
                </SelectOption>
              );
            })}
          </SelectList>
        </Select>
      </FlexItem>
    </Flex>
  );
}

const getPlatformValue = (manifest: Manifest) =>
  `${manifest.platform.os} on ${manifest.platform.architecture}`;

type ArchSelectProps = {
  digest: string;
  options: Manifest[];
  setDigest: (digest: string) => void;
  render: boolean;
  style?: React.CSSProperties;
};
