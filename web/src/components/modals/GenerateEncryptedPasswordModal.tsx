import {Modal, ModalVariant, Button, TextInput} from '@patternfly/react-core';
import {useState, useEffect} from 'react';
import FormError from 'src/components/errors/FormError';
import {addDisplayError} from 'src/resources/ErrorHandling';
import {useCreateClientKey} from 'src/hooks/UseCreateClientKey';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
import CredentialsModal, {Credentials} from './CredentialsModal';

export function GenerateEncryptedPassword(props: ConfirmationModalProps) {
  const [err, setErr] = useState<string>();
  const {user} = useCurrentUser();

  const [password, setPassword] = useState('');
  const [step, setStep] = useState(1);
  const {createClientKey, clientKey} = useCreateClientKey({
    onError: (error) => {
      console.error(error);
      setErr(addDisplayError('Error', error));
    },
    onSuccess: () => {
      setErr(undefined); // Clear any previous errors
      setStep(step + 1);
    },
  });

  const handleModalConfirm = async () => {
    createClientKey(password);
  };

  const handleClose = () => {
    props.toggleModal();
  };

  // Cleanup state when modal closes
  useEffect(() => {
    if (!props.modalOpen) {
      setStep(1);
      setPassword('');
      setErr(undefined);
    }
  }, [props.modalOpen]);

  // Step 2: Show credentials modal with all credential formats
  // Only transition to step 2 if we have clientKey, user, and no error
  if (step === 2 && clientKey && user && !err) {
    const credentials: Credentials = {
      username: user.username,
      password: clientKey,
      title: user.username,
    };

    return (
      <CredentialsModal
        isOpen={props.modalOpen}
        onClose={handleClose}
        credentials={credentials}
        type="encrypted-password"
      />
    );
  }

  // Step 1: Password input
  return (
    <Modal
      variant={ModalVariant.small}
      title={props.title}
      isOpen={props.modalOpen}
      onClose={handleClose}
      actions={[
        <Button
          key="confirm"
          variant="primary"
          onClick={handleModalConfirm}
          id="submit"
        >
          {props.buttonText}
        </Button>,
        <Button key="cancel" variant="link" onClick={handleClose}>
          Cancel
        </Button>,
      ]}
    >
      <FormError message={err} setErr={setErr} />
      <TextInput
        id="delete-confirmation-input"
        value={password}
        type="password"
        onChange={(_, value) => setPassword(value)}
        aria-label="text input example"
        label="Password"
      />
      Please enter your password in order to generate
    </Modal>
  );
}

type ConfirmationModalProps = {
  title: string;
  modalOpen: boolean;
  buttonText: string;
  toggleModal: () => void;
};
