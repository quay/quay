import {
  FormGroup,
  TextInput,
  ValidatedOptions,
  HelperText,
  HelperTextItem,
} from '@patternfly/react-core';
import Conditional from 'src/components/empty/Conditional';
import {NotificationEventConfig} from 'src/hooks/UseEvents';
import {useState} from 'react';

export default function RepoEventExpiry(props: RepoEventExpiryProps) {
  const [valid, setValid] = useState<ValidatedOptions>(
    ValidatedOptions.default,
  );

  const onChange = (_event, value) => {
    props.setEventConfig({days: Number(value)});
    if (value < 1) {
      setValid(ValidatedOptions.error);
    } else {
      setValid(ValidatedOptions.success);
    }
  };

  return (
    <FormGroup
      fieldId="event"
      label="When the image is due to expiry in days"
      isRequired
    >
      <TextInput
        value={props.eventConfig?.days || ''}
        onChange={onChange}
        type={'number'}
        id="days-to-image-expiry"
        required
        validated={valid}
      />
      <Conditional if={valid == ValidatedOptions.error}>
        <HelperText>
          <HelperTextItem variant="error" hasIcon>
            number of days should be more than 0.
          </HelperTextItem>
        </HelperText>
      </Conditional>
    </FormGroup>
  );
}

interface RepoEventExpiryProps {
  eventConfig: NotificationEventConfig;
  setEventConfig: (val) => void;
}
