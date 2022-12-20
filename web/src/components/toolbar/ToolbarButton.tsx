import {Button, ToolbarItem} from '@patternfly/react-core';

export function ToolbarButton(props: ToolbarButtonProps) {
  return (
    <ToolbarItem>
      <Button
        id={props.id}
        variant="primary"
        onClick={() => props.setModalOpen(true)}
      >
        {props.buttonValue}
      </Button>
      {props.isModalOpen ? props.Modal : null}{' '}
    </ToolbarItem>
  );
}

type ToolbarButtonProps = {
  id: string;
  buttonValue: string;
  Modal: object;
  isModalOpen: boolean;
  setModalOpen: (open) => void;
};
