import {Form, FormGroup, TextInput} from '@patternfly/react-core';
import ExclamationCircleIcon from '@patternfly/react-icons/dist/esm/icons/exclamation-circle-icon';
import {useEffect, useState} from 'react';

type validate = 'success' | 'error' | 'default';

export default function NameAndDescription(props: NameAndDescriptionProps) {
  const [validatedName, setValidatedName] = useState<validate>('default');
  const [nameHelperText, setNameHelperText] = useState(props.nameHelperText);

  const handleNameChange = (robotName: string) => {
    props.setName(robotName);
    setNameHelperText('Validating...');
  };

  useEffect(() => {
    if (props.name == '') {
      setValidatedName('default');
      setNameHelperText(props.nameHelperText);
      return;
    }
    if (props.validateName()) {
      setValidatedName('success');
    } else {
      setValidatedName('error');
    }
    setNameHelperText(props.nameHelperText);
  }, [props.name]);

  return (
    <Form>
      <FormGroup
        label={props.nameLabel}
        fieldId="form-name"
        isRequired
        helperText={nameHelperText}
        helperTextInvalid={nameHelperText}
        validated={validatedName}
        helperTextInvalidIcon={<ExclamationCircleIcon />}
      >
        <TextInput
          isRequired
          type="text"
          id="robot-wizard-form-name"
          name="form-name"
          value={props.name}
          onChange={handleNameChange}
          validated={validatedName}
        />
      </FormGroup>
      <FormGroup
        label={props.descriptionLabel}
        fieldId="form-description"
        helperText={props.helperText}
      >
        <TextInput
          type="text"
          id="robot-wizard-form-description"
          name="form-description"
          value={props.description}
          onChange={(robotDescription: string) =>
            props.setDescription(robotDescription)
          }
        />
      </FormGroup>
    </Form>
  );
}

interface NameAndDescriptionProps {
  name: string;
  setName: (robotName) => void;
  description: string;
  setDescription: (robotDescription) => void;
  nameLabel: string;
  descriptionLabel: string;
  helperText: string;
  nameHelperText: string;
  validateName: () => boolean;
}
