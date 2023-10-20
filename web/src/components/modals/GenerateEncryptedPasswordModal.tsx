import {Modal, ModalVariant, Button, TextInput} from '@patternfly/react-core';
import {useState} from 'react';
import FormError from 'src/components/errors/FormError';
import {addDisplayError} from 'src/resources/ErrorHandling';
import {useCreateClientKey} from 'src/hooks/UseCreateClientKey';

export function GenerateEncryptedPassword(props: ConfirmationModalProps) {
  const [err, setErr] = useState<string>();

  const [password, setPassword] = useState('');
  const [step, setStep] = useState(1);
  const {createClientKey, clientKey} = useCreateClientKey({
    onError: (error) => {
      console.error(error);
      setErr(addDisplayError('Error', error));
    },
    onSuccess: () => {
      setStep(step + 1);
    },
  });

  const handleModalConfirm = async () => {
    createClientKey(password);
  };

  return (
    <Modal
      variant={ModalVariant.small}
      title={props.title}
      isOpen={props.modalOpen}
      onClose={props.toggleModal}
      actions={
        step == 1
          ? [
              <Button
                key="confirm"
                variant="primary"
                onClick={handleModalConfirm}
                id="submit"
              >
                {props.buttonText}
              </Button>,
              <Button key="cancel" variant="link" onClick={props.toggleModal}>
                Cancel
              </Button>,
            ]
          : [
              <Button key="cancel" variant="link" onClick={props.toggleModal}>
                Done
              </Button>,
            ]
      }
    >
      {step == 1 && (
        <>
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
        </>
      )}
      {step == 2 && (
        <>
          Your encrypted password is: <br /> {clientKey}
        </>
      )}
    </Modal>
  );
}

type ConfirmationModalProps = {
  title: string;
  modalOpen: boolean;
  buttonText: string;
  toggleModal: () => void;
};
