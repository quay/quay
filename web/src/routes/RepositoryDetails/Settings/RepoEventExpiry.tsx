import {FormGroup, TextInput, ValidatedOptions} from '@patternfly/react-core';
import {NotificationEventConfig} from 'src/hooks/UseEvents';
import {useState} from 'react';

export default function RepoEventExpiry(props: RepoEventExpiryProps) {
  const [valid, setValid] = useState(ValidatedOptions.default);

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
        value={props.eventConfig?.days}
        onChange={onChange}
        type={'number'}
        id="days-to-image-expiry"
        required
        validated={valid}
      />
    </FormGroup>
  );
}

interface RepoEventExpiryProps {
  eventConfig: NotificationEventConfig;
  setEventConfig: (val) => void;
}
