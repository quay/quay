import {Button, Modal, ModalVariant} from '@patternfly/react-core';
import Labels, {LabelsVariant} from 'src/components/labels/Labels';

export default function EditLabelsModal(props: EditLabelsModalProps) {
  return (
    <>
      <Modal
        id="edit-labels-modal"
        title="Edit labels"
        isOpen={props.isOpen}
        onClose={() => props.setIsOpen(false)}
        variant={ModalVariant.medium}
      >
        <Labels
          org={props.org}
          repo={props.repo}
          digest={props.manifest}
          variant={LabelsVariant.Editable}
          onComplete={props.onComplete}
        />
      </Modal>
    </>
  );
}

interface EditLabelsModalProps {
  org: string;
  repo: string;
  manifest: string;
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
  onComplete?: () => void;
}
