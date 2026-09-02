import {
  FormGroup,
  TextInput,
  HelperText,
  HelperTextItem,
} from '@patternfly/react-core';
import {NotificationEventConfig} from 'src/hooks/UseEvents';

export default function RepoEventVulnTagRegex(
  props: RepoEventVulnTagRegexProps,
) {
  const onChange = (_event, value) => {
    props.setEventConfig({...props.eventConfig, 'tag-regex': value});
  };

  return (
    <FormGroup fieldId="vulnerability-tag-regex" label="Matching tag(s)">
      <TextInput
        value={props.eventConfig?.['tag-regex'] || ''}
        onChange={onChange}
        type="text"
        id="vulnerability-tag-regex"
        data-testid="vulnerability-tag-regex"
        placeholder="(v2\..*)|(latest)"
      />
      <HelperText>
        <HelperTextItem>
          An optional regular expression for matching the tag(s) referencing the
          vulnerable image. If left blank, the notification will fire for all
          tags.
        </HelperTextItem>
      </HelperText>
    </FormGroup>
  );
}

interface RepoEventVulnTagRegexProps {
  eventConfig: NotificationEventConfig;
  setEventConfig: (val: NotificationEventConfig) => void;
}
