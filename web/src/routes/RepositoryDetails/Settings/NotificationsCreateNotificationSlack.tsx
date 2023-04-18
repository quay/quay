import {NotificationEvent} from 'src/hooks/UseEvents';
import {NotificationMethod} from 'src/hooks/UseNotificationMethods';
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
import {useEffect, useState} from 'react';
import {useUpdateNotifications} from 'src/hooks/UseUpdateNotifications';
import {ExclamationCircleIcon} from '@patternfly/react-icons';

export default function CreateSlackNotification(
  props: CreateSlackNotificationProps,
) {
  const [url, setUrl] = useState<string>('');
  const [title, setTitle] = useState<string>('');
  const {
    create,
    successCreatingNotification,
    errorCreatingNotification,
    resetCreatingNotification,
  } = useUpdateNotifications(props.org, props.repo);

  const isValidWebhookURL = (url: string) => {
    const regex =
      /^https:\/\/hooks\.slack\.com\/services\/[A-Z0-9]+\/[A-Z0-9]+\/[a-zA-Z0-9]+$/;
    return regex.test(url);
  };

  const isFormComplete =
    props.method != undefined &&
    props.event != undefined &&
    url != '' &&
    isValidWebhookURL(url);

  const createNotification = async () => {
    create({
      config: {
        url: url,
      },
      event: props.event?.type,
      event_config: {},
      method: props.method?.type,
      title: title,
    });
  };

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

  return (
    <>
      <FormGroup
        fieldId="slack-webhook-url"
        label="Webhook URL"
        isRequired
        helperTextInvalid="Must be a valid slack url in the form ^https://hooks.slack.com/services/[A-Z0-9]+/[A-Z0-9]+/[a-zA-Z0-9]+$/"
        helperTextInvalidIcon={<ExclamationCircleIcon />}
        validated={url == '' || isValidWebhookURL(url) ? 'default' : 'error'}
      >
        <TextInput
          required
          id="slack-webhook-url-field"
          value={url}
          onChange={(value) => setUrl(value)}
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

interface CreateSlackNotificationProps {
  org: string;
  repo: string;
  event: NotificationEvent;
  method: NotificationMethod;
  closeDrawer: () => void;
  setError: (error: string) => void;
}
