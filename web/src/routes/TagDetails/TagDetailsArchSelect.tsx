import {
  Select,
  SelectOption,
  SelectVariant,
  Flex,
  FlexItem,
} from '@patternfly/react-core';
import {useState} from 'react';
import {Manifest} from 'src/resources/TagResource';

export default function ArchSelect(props: ArchSelectProps) {
  if (!props.render) return null;
  const [isSelectOpen, setIsSelectOpen] = useState<boolean>();

  return (
    <Flex>
      <FlexItem>Architecture</FlexItem>
      <FlexItem>
        <Select
          variant={SelectVariant.single}
          placeholderText="Architecture"
          aria-label="Architecture select"
          onToggle={() => {
            setIsSelectOpen(!isSelectOpen);
          }}
          onSelect={(e, digest) => {
            props.setDigest(digest as string);
            setIsSelectOpen(false);
          }}
          selections={props.digest}
          isOpen={isSelectOpen}
          data-testid="arch-select"
        >
          {props.options.map((manifest, index) => (
            <SelectOption key={index} value={manifest.digest}>
              {' '}
              {`${manifest.platform.os} on ${manifest.platform.architecture}`}{' '}
            </SelectOption>
          ))}
        </Select>
      </FlexItem>
    </Flex>
  );
}

type ArchSelectProps = {
  digest: string;
  options: Manifest[];
  setDigest: (digest: string) => void;
  render: boolean;
};
