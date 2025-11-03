import {useState} from 'react';
import {
  Modal,
  ModalVariant,
  Button,
  Alert,
  AlertVariant as PFAlertVariant,
} from '@patternfly/react-core';
import {useSendRecoveryEmail} from 'src/hooks/UseUserActions';
import {AlertVariant, useUI} from 'src/contexts/UIContext';

interface SendRecoveryEmailModalProps {
  isOpen: boolean;
  onClose: () => void;
  username: string;
}

export default function SendRecoveryEmailModal(
  props: SendRecoveryEmailModalProps,
) {
  const [error, setError] = useState<string | null>(null);
  const [successEmail, setSuccessEmail] = useState<string | null>(null);
  const {addAlert} = useUI();

  const {sendRecovery, isLoading} = useSendRecoveryEmail({
    onSuccess: (data) => {
      setSuccessEmail(data.email);
      addAlert({
        variant: AlertVariant.Success,
        title: `Recovery email sent to ${data.email}`,
      });
    },
    onError: (err) => {
      const errorMessage =
        err?.response?.data?.error_message ||
        err?.response?.data?.detail ||
        'Failed to send recovery email';
      setError(errorMessage);
      addAlert({
        variant: AlertVariant.Failure,
        title: `Failed to send recovery email for ${props.username}`,
        message: errorMessage,
      });
    },
  });

  const handleClose = () => {
    setError(null);
    setSuccessEmail(null);
    props.onClose();
  };

  const handleSend = () => {
    setError(null);
    sendRecovery(props.username);
  };

  return (
    <Modal
      title={successEmail ? 'Recovery Email Sent' : `Send Recovery Email`}
      isOpen={props.isOpen}
      onClose={handleClose}
      variant={ModalVariant.medium}
      actions={
        successEmail
          ? [
              <Button key="close" variant="primary" onClick={handleClose}>
                Close
              </Button>,
            ]
          : [
              <Button
                key="confirm"
                variant="primary"
                onClick={handleSend}
                isLoading={isLoading}
                isDisabled={isLoading}
              >
                Send Recovery Email
              </Button>,
              <Button key="cancel" variant="link" onClick={handleClose}>
                Cancel
              </Button>,
            ]
      }
    >
      {successEmail ? (
        <Alert variant={PFAlertVariant.success} title="Success" isInline>
          A recovery email has been sent to {successEmail}
        </Alert>
      ) : (
        <>
          <p>
            Are you sure you want to send a recovery email to{' '}
            <strong>{props.username}</strong>?
          </p>
          <p>
            This will send a password reset link to the user&apos;s registered
            email address.
          </p>
          {error && (
            <Alert variant={PFAlertVariant.danger} title="Error" isInline>
              {error}
            </Alert>
          )}
        </>
      )}
    </Modal>
  );
}
