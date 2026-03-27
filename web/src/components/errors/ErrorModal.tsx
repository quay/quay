import {
  Modal,
  ModalVariant,
  ModalHeader,
  ModalBody,
} from '@patternfly/react-core';
import {ExclamationCircleIcon} from '@patternfly/react-icons';

export default function ErrorModal(props: ErrorModalProps) {
  let err = props.error;
  if (Array.isArray(err)) {
    err = err.map((e) => (
      <div key={e}>
        <ExclamationCircleIcon color="red" /> {e}
        <br />
      </div>
    ));
  }

  return (
    <Modal
      variant={ModalVariant.small}
      aria-label="error modal"
      isOpen={props.error != null}
      onClose={() => props.setError(null)}
    >
      <ModalHeader title={props.title} />
      <ModalBody>{err}</ModalBody>
    </Modal>
  );
}

interface ErrorModalProps {
  error: string | string[] | React.ReactNode;
  setError: (err: any) => void;
  title?: string;
}
