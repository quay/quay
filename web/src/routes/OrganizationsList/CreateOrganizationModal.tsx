import {
  Modal,
  ModalVariant,
  Button,
  Form,
  FormGroup,
  TextInput,
} from '@patternfly/react-core';
import './css/Organizations.scss';
import {isValidEmail} from 'src/libs/utils';
import {useState} from 'react';
import FormError from 'src/components/errors/FormError';
import {addDisplayError} from 'src/resources/ErrorHandling';
import {useCreateOrganization} from 'src/hooks/UseCreateOrganization';

interface Validation {
  message: string;
  isValid: boolean;
  type: 'default' | 'error' | 'warning';
}

const defaultMessage: Validation = {
  message:
    'This will also be the namespace for your repositories. Must be alphanumeric, all lowercase, at least 2 characters long and at most 255 characters long',
  isValid: true,
  type: 'default',
};

export const CreateOrganizationModal = (
  props: CreateOrganizationModalProps,
): JSX.Element => {
  const [organizationName, setOrganizationName] = useState('');
  const [organizationEmail, setOrganizationEmail] = useState('');
  const [invalidEmailFlag, setInvalidEmailFlag] = useState(false);
  const [validation, setValidation] = useState<Validation>(defaultMessage);
  const [err, setErr] = useState<string>();

  const {createOrganization} = useCreateOrganization({
    onSuccess: () => props.handleModalToggle(),
    onError: (err) => {
      setErr(addDisplayError('Unable to create organization', err));
    },
  });

  const handleNameInputChange = (value: any) => {
    const regex = /^([a-z0-9]+(?:[._-][a-z0-9]+)*)$/;
    if (!regex.test(value) || value.length >= 256 || value.length < 2) {
      setValidation({
        message:
          'Must be alphanumeric, all lowercase, at least 2 characters long and at most 255 characters long',
        isValid: false,
        type: 'error',
      });
    } else if (value.length > 30 || value.length < 4) {
      setValidation({
        message:
          'Namespaces less than 4 or more than 30 characters are only compatible with Docker 1.6+',
        isValid: true,
        type: 'warning',
      });
    } else if (value.includes('.') || value.includes('-')) {
      setValidation({
        message:
          'Namespaces with dashes or dots are only compatible with Docker 1.9+',
        isValid: true,
        type: 'warning',
      });
    } else {
      setValidation(defaultMessage);
    }
    setOrganizationName(value);
  };

  const handleEmailInputChange = (value: any) => {
    setOrganizationEmail(value);
  };

  const createOrganizationHandler = async () => {
    await createOrganization(organizationName, organizationEmail);
  };

  const onInputBlur = () => {
    if (organizationEmail.length !== 0) {
      isValidEmail(organizationEmail)
        ? setInvalidEmailFlag(false)
        : setInvalidEmailFlag(true);
    } else {
      return;
    }
  };

  return (
    <Modal
      title="Create Organization"
      variant={ModalVariant.large}
      isOpen={props.isModalOpen}
      onClose={props.handleModalToggle}
      actions={[
        <Button
          id="create-org-confirm"
          key="confirm"
          variant="primary"
          onClick={createOrganizationHandler}
          form="modal-with-form-form"
          isDisabled={
            invalidEmailFlag || !organizationName || !validation.isValid
          }
        >
          Create
        </Button>,
        <Button
          id="create-org-cancel"
          key="cancel"
          variant="link"
          onClick={props.handleModalToggle}
        >
          Cancel
        </Button>,
      ]}
    >
      <FormError message={err} setErr={setErr} />
      <Form id="create-org-modal" isWidthLimited>
        <FormGroup
          isInline
          label="Organization Name"
          isRequired
          fieldId="create-org-name"
          helperText={validation.message}
          helperTextInvalid={validation.message}
          validated={validation.type}
        >
          <TextInput
            isRequired
            type="text"
            id="create-org-name-input"
            value={organizationName}
            onChange={handleNameInputChange}
            validated={validation.type}
          />
        </FormGroup>
        <FormGroup
          label="Organization Email"
          fieldId="create-org-email"
          helperText="This address must be different from your account's email"
          helperTextInvalid={'Enter a valid email: email@provider.com'}
          validated={invalidEmailFlag ? 'error' : 'default'}
        >
          <TextInput
            type="email"
            id="create-org-email-input"
            name="create-org-email-input"
            value={organizationEmail}
            onChange={handleEmailInputChange}
            validated={invalidEmailFlag ? 'error' : 'default'}
            onBlur={onInputBlur}
          />
        </FormGroup>
        <br />
      </Form>
    </Modal>
  );
};

type CreateOrganizationModalProps = {
  isModalOpen: boolean;
  handleModalToggle?: () => void;
};
