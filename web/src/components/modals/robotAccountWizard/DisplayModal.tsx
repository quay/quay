import {Modal, ModalVariant, Button} from '@patternfly/react-core';

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
      <Button key="cancel" variant="link" onClick={handleModalToggle}>
        Cancel
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
      title={props.title}
      isOpen={props.isModalOpen}
      onClose={handleModalToggle}
      footer={props.showSave ? footerWithSave : footerWithoutSave}
    >
      {props.Component}
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
}
