import {Button, Flex, InputGroup, TextInput} from '@patternfly/react-core';
import {EyeIcon, EyeSlashIcon} from '@patternfly/react-icons';
import {useState} from 'react';

export default function ReadonlySecret(props: ReadonlySecretProps) {
  const [secretHidden, setSecretHidden] = useState<boolean>(true);
  return (
    <Flex direction={{default: 'row'}}>
      {props.label}
      {':'}
      <InputGroup style={{width: 'inherit'}}>
        <TextInput
          type={secretHidden ? 'password' : 'text'}
          aria-label="secret input"
          value={props.secret}
          isDisabled
          style={{
            backgroundColor: 'white',
            width: `${props.secret.length}ch`,
            paddingRight: 0,
            cursor: 'auto',
          }}
        />
        <Button
          variant="plain"
          onClick={() => setSecretHidden(!secretHidden)}
          aria-label={secretHidden ? 'Show secret' : 'Hide secret'}
          style={{paddingLeft: 0}}
        >
          {secretHidden ? <EyeIcon /> : <EyeSlashIcon />}
        </Button>
      </InputGroup>
    </Flex>
  );
}

interface ReadonlySecretProps {
  label: string;
  secret: string;
}
