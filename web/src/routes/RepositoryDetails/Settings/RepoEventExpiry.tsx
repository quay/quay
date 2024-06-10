import {FormGroup, TextInput} from '@patternfly/react-core';
import {NotificationEventConfig} from 'src/hooks/UseEvents';

export default function RepoEventExpiry(props: RepoEventExpiryProps) {
  const onChange = (_event, value) => {
    props.setEventConfig({days: value});
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
      />
    </FormGroup>
  );
}

interface RepoEventExpiryProps {
  eventConfig: NotificationEventConfig;
  setEventConfig: (val) => void;
}
