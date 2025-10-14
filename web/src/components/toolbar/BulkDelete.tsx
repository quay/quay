import {Button} from '@patternfly/react-core';
import {TrashIcon} from '@patternfly/react-icons';

export function BulkDelete(props: BulkDeleteProps) {
  return (
    <Button
      icon={<TrashIcon color="#6a6e73" />}
      variant="plain"
      aria-label="Action"
      onClick={() => props.setClicked(true)}
    />
  );
}

type BulkDeleteProps = {
  setClicked: (boolean) => void;
};
