import {
  Button,
  Modal,
  ModalVariant,
  ModalHeader,
  ModalBody,
  ModalFooter,
} from '@patternfly/react-core';

export default function DisplayModal(props: DisplayModalProps) {
  const handleModalToggle = () => {
    props.setIsModalOpen(!props.isModalOpen);
    if (props.onClose) {
      props.onClose();
    }
  };

  const onSave = () => {
    props.onSave();
  };

  const footerWithoutSave = (
    <>
      <Button key="close" variant="primary" onClick={handleModalToggle}>
        Close
      </Button>
    </>
  );

  const footerWithSave = (
    <>
      <Button key="save" variant="primary" onClick={onSave}>
        Save
      </Button>
      <Button key="cancel" variant="link" onClick={handleModalToggle}>
        Cancel
      </Button>
    </>
  );

  return (
    <Modal
      variant={ModalVariant.large}
      isOpen={props.isModalOpen}
      onClose={handleModalToggle}
    >
      <ModalHeader title={props.title} />
      <ModalBody>{props.Component}</ModalBody>
      {props.showFooter && (
        <ModalFooter>
          {props.showSave ? footerWithSave : footerWithoutSave}
        </ModalFooter>
      )}
    </Modal>
  );
}

interface DisplayModalProps {
  isModalOpen: boolean;
  setIsModalOpen: (boolean) => void;
  title: string;
  Component: any;
  onClose?: () => void;
  onSave?: () => void;
  showSave: boolean;
  showFooter?: boolean;
}
