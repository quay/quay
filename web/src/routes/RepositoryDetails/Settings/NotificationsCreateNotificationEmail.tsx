import {
  ActionGroup,
  Alert,
  AlertActionCloseButton,
  Button,
  FormGroup,
  Modal,
  ModalVariant,
  TextInput,
} from '@patternfly/react-core';
import {ExclamationCircleIcon} from '@patternfly/react-icons';
import {useEffect, useState} from 'react';
import Conditional from 'src/components/empty/Conditional';
import {useAuthorizedEmails} from 'src/hooks/UseAuthorizedEmails';
import {NotificationEvent} from 'src/hooks/UseEvents';
import {NotificationMethod} from 'src/hooks/UseNotificationMethods';
import {useUpdateNotifications} from 'src/hooks/UseUpdateNotifications';
import {isValidEmail} from 'src/libs/utils';
import {fetchAuthorizedEmail} from 'src/resources/AuthorizedEmailResource';

export default function CreateEmailNotification(
  props: CreateEmailNotification,
) {
  const [title, setTitle] = useState<string>('');
  const [email, setEmail] = useState<string>('');
  const [isEmailAuthModalOpen, setIsEmailAuthModalOpen] = useState<boolean>();
  const {
    create,
    successCreatingNotification,
    errorCreatingNotification,
    resetCreatingNotification,
  } = useUpdateNotifications(props.org, props.repo);
  const {
    emailConfirmed,
    resetEmailConfirmed,
    polling,
    startPolling,
    stopPolling,
    errorPolling,
    sendAuthorizedEmail,
    successSendingAuthorizedEmail,
    errorSendingAuthorizedEmail,
    resetSendAuthorizationEmail,
  } = useAuthorizedEmails(props.org, props.repo);

  const isFormComplete =
    props.method != undefined &&
    props.event != undefined &&
    email != undefined &&
    email != '' &&
    isValidEmail(email);

  useEffect(() => {
    if (successSendingAuthorizedEmail) {
      startPolling(email);
      resetSendAuthorizationEmail();
      setIsEmailAuthModalOpen(false);
    }
  }, [successSendingAuthorizedEmail]);

  useEffect(() => {
    if (emailConfirmed) {
      create({
        config: {
          email: email,
        },
        event: props.event?.type,
        event_config: {},
        method: props.method?.type,
        title: title,
      });
      resetEmailConfirmed();
    }
  }, [emailConfirmed]);

  useEffect(() => {
    if (successCreatingNotification) {
      resetCreatingNotification();
      props.closeDrawer();
    }
  }, [successCreatingNotification]);

  useEffect(() => {
    if (errorCreatingNotification) {
      props.setError('Unable to create notification');
      resetCreatingNotification();
    }
  }, [errorCreatingNotification]);

  const createNotification = async () => {
    let emailStatus = null;
    try {
      emailStatus = await fetchAuthorizedEmail(props.org, props.repo, email);
    } catch (err) {
      props.setError('Unable to verify email');
    }
    if (emailStatus != null && emailStatus.confirmed) {
      create({
        config: {
          email: email,
        },
        event: props.event?.type,
        event_config: {},
        method: props.method?.type,
        title: title,
      });
    } else {
      setIsEmailAuthModalOpen(true);
    }
  };

  return (
    <>
      <Modal
        variant={ModalVariant.small}
        title="Email Authorization"
        isOpen={isEmailAuthModalOpen}
        onClose={() => setIsEmailAuthModalOpen(false)}
        actions={[
          <Button
            key="sendemail"
            variant="primary"
            onClick={() => sendAuthorizedEmail(email)}
          >
            Send Authorized Email
          </Button>,
          <Button
            key="cancel"
            variant="link"
            onClick={() => setIsEmailAuthModalOpen(false)}
          >
            Cancel
          </Button>,
        ]}
      >
        <Conditional if={errorSendingAuthorizedEmail}>
          <Alert
            isInline
            actionClose={
              <AlertActionCloseButton onClose={resetSendAuthorizationEmail} />
            }
            variant="danger"
            title="Failure sending authorized email"
          />
        </Conditional>
        The email address {email} has not been authorized to recieve
        notifications from this repository. Please click &lsquo;Send Authorized
        Email&lsquo; to start the authorization process.
      </Modal>
      <Modal
        variant={ModalVariant.small}
        title="Email Authorization"
        isOpen={polling}
        onClose={stopPolling}
        actions={[
          <Button key="cancel" variant="primary" onClick={stopPolling}>
            Cancel
          </Button>,
        ]}
      >
        An email has been sent to {email}. Please click the link contained in
        the email.
      </Modal>
      <Modal
        variant={ModalVariant.small}
        title="Email Authorization"
        isOpen={errorPolling}
        actions={[
          <Button
            key="cancel"
            variant="primary"
            onClick={() => startPolling(email)}
          >
            Retry
          </Button>,
        ]}
      >
        Unable to verify email confirmation. Please wait a moment and retry.
      </Modal>
      <FormGroup
        fieldId="email"
        label="E-mail address"
        isRequired
        validated={email == '' || isValidEmail(email) ? 'default' : 'error'}
        helperTextInvalid="Invalid email"
        helperTextInvalidIcon={<ExclamationCircleIcon />}
      >
        <TextInput
          id="notification-email"
          isRequired
          value={email}
          onChange={(value) => setEmail(value)}
        />
      </FormGroup>
      <FormGroup fieldId="title" label="Title">
        <TextInput
          id="notification-title"
          value={title}
          onChange={(value) => setTitle(value)}
        />
      </FormGroup>
      <ActionGroup>
        <Button
          isDisabled={!isFormComplete}
          onClick={createNotification}
          variant="primary"
        >
          Submit
        </Button>
      </ActionGroup>
    </>
  );
}

interface CreateEmailNotification {
  org: string;
  repo: string;
  event: NotificationEvent;
  method: NotificationMethod;
  closeDrawer: () => void;
  setError: (error: string) => void;
}
