import {NotificationEvent} from 'src/hooks/UseEvents';
import {NotificationMethod} from 'src/hooks/UseNotificationMethods';
import {
  ActionGroup,
  Button,
  FormGroup,
  FormHelperText,
  HelperText,
  HelperTextItem,
  TextArea,
  TextInput,
} from '@patternfly/react-core';
import {useEffect, useState} from 'react';
import {useUpdateNotifications} from 'src/hooks/UseUpdateNotifications';
import {NotificationEventConfig} from 'src/hooks/UseEvents';
import {ExclamationCircleIcon} from '@patternfly/react-icons';

export default function CreateWebhookNotification(
  props: CreateWebhookNotificationProps,
) {
  const [url, setUrl] = useState<string>('');
  const [jsonBody, setJsonBody] = useState<string>('');
  const [title, setTitle] = useState<string>('');
  const {
    create,
    successCreatingNotification,
    errorCreatingNotification,
    resetCreatingNotification,
  } = useUpdateNotifications(props.org, props.repo);

  const isValidURL = (url: string) => {
    return url.startsWith('http://') || url.startsWith('https://');
  };

  const isFormComplete =
    props.method != undefined &&
    props.event != undefined &&
    url != '' &&
    props.isValidateConfig() &&
    isValidURL(url);

  const createNotification = async () => {
    create({
      config: {
        url: url,
        template: jsonBody,
      },
      event: props.event?.type,
      event_config: props.eventConfig,
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
      props.setError(errorCreatingNotification as string);
      resetCreatingNotification();
    }
  }, [errorCreatingNotification]);

  return (
    <>
      <FormGroup fieldId="webhook-url" label="Webhook URL" isRequired>
        <TextInput
          required
          id="webhook-url-field"
          value={url}
          onChange={(_event, value) => setUrl(value)}
        />

        {!isValidURL(url) && (
          <FormHelperText>
            <HelperText>
              <HelperTextItem variant="error" icon={<ExclamationCircleIcon />}>
                URL must begin with http(s)://
              </HelperTextItem>
            </HelperText>
          </FormHelperText>
        )}
      </FormGroup>
      <FormGroup fieldId="webhook-body" label="POST JSON body template">
        <TextArea
          id="json-body-field"
          value={jsonBody}
          onChange={(_event, value) => setJsonBody(value)}
        />
      </FormGroup>
      <FormGroup fieldId="title" label="Title">
        <TextInput
          id="notification-title"
          value={title}
          onChange={(_event, value) => setTitle(value)}
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

interface CreateWebhookNotificationProps {
  org: string;
  repo: string;
  event: NotificationEvent;
  method: NotificationMethod;
  eventConfig: NotificationEventConfig;
  isValidateConfig: () => boolean;
  closeDrawer: () => void;
  setError: (error: string) => void;
}
