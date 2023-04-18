import {Button} from '@patternfly/react-core';
import {TrashIcon} from '@patternfly/react-icons';

export function BulkDelete(props: BulkDeleteProps) {
  return (
    <Button
      variant="plain"
      aria-label="Action"
      onClick={() => props.setClicked(true)}
    >
      <TrashIcon color="#6a6e73" />
    </Button>
  );
}

type BulkDeleteProps = {
  setClicked: (boolean) => void;
};
