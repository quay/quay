import {Form, FormGroup, TextInput} from '@patternfly/react-core';
import ExclamationCircleIcon from '@patternfly/react-icons/dist/esm/icons/exclamation-circle-icon';

export default function NameAndDescription(props: NameAndDescriptionProps) {
  return (
    <Form>
      <FormGroup
        label={props.nameLabel}
        fieldId="form-name"
        isRequired
        helperTextInvalidIcon={<ExclamationCircleIcon />}
      >
        <TextInput
          data-testid="create-team-wizard-form-name"
          isRequired
          type="text"
          id="create-team-wizard-form-name"
          name="form-name"
          value={props.name}
          aria-label="disabled teamName input"
          isDisabled
        />
      </FormGroup>
      <FormGroup
        label={props.descriptionLabel}
        fieldId="form-description"
        helperText={props.helperText}
      >
        <TextInput
          data-testid="create-team-wizard-form-description"
          type="text"
          id="create-team-wizard-form-description"
          name="form-description"
          value={props.description}
          aria-label="disabled teamDescription input"
          isDisabled
        />
      </FormGroup>
    </Form>
  );
}

interface NameAndDescriptionProps {
  name: string;
  setName?: (robotName) => void;
  description: string;
  setDescription?: (descr: string) => void;
  nameLabel: string;
  descriptionLabel: string;
  helperText?: string;
  nameHelperText?: string;
  validateName?: (string) => boolean;
}
