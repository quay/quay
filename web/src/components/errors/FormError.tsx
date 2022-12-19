import {Alert, AlertActionCloseButton} from '@patternfly/react-core';
import {isErrorString} from 'src/resources/ErrorHandling';

export default function FormError(props: FormErrorProps) {
  if (!isErrorString(props.message)) {
    return null;
  }
  return (
    <Alert
      id="form-error-alert"
      isInline
      actionClose={<AlertActionCloseButton onClose={() => props.setErr('')} />}
      variant="danger"
      title={props.message}
    />
  );
}

interface FormErrorProps {
  message: string;
  setErr: (tag: string) => void;
}
