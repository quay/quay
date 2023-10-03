import {
  Form,
  FormGroup,
  FormHelperText,
  HelperText,
  HelperTextItem,
  TextInput,
} from '@patternfly/react-core';
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
      <FormGroup label={props.nameLabel} fieldId="form-name" isRequired>
        <TextInput
          data-testid="new-robot-name-input"
          isRequired
          type="text"
          id="robot-wizard-form-name"
          name="form-name"
          value={props.name}
          onChange={(_event, robotName: string) => handleNameChange(robotName)}
          validated={validatedName}
        />

        <FormHelperText>
          <HelperText>
            <HelperTextItem
              variant={validatedName}
              {...(validatedName === 'error' && {
                icon: <ExclamationCircleIcon />,
              })}
            >
              {nameHelperText}
            </HelperTextItem>
          </HelperText>
        </FormHelperText>
      </FormGroup>
      <FormGroup label={props.descriptionLabel} fieldId="form-description">
        <TextInput
          data-testid="new-robot-description-input"
          type="text"
          id="robot-wizard-form-description"
          name="form-description"
          value={props.description}
          onChange={(_event, robotDescription: string) =>
            props.setDescription(robotDescription)
          }
        />

        <FormHelperText>
          <HelperText>
            <HelperTextItem>{props.helperText}</HelperTextItem>
          </HelperText>
        </FormHelperText>
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
