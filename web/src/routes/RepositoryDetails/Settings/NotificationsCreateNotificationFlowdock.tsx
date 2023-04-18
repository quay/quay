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

export default function CreateFlowdockNotification(
  props: CreateFlowdockNotification,
) {
  const [title, setTitle] = useState<string>('');
  const [apiTopken, setAPIToken] = useState<string>('');
  const {
    create,
    successCreatingNotification,
    errorCreatingNotification,
    resetCreatingNotification,
  } = useUpdateNotifications(props.org, props.repo);

  const isFormComplete =
    props.method != undefined && props.event != undefined && apiTopken != '';

  const createNotification = async () => {
    create({
      config: {
        flow_api_token: apiTopken,
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
        fieldId="flowdock-api-token"
        label="Flowdock API token"
        isRequired
      >
        <TextInput
          required
          id="flowdock-api-token-field"
          value={apiTopken}
          onChange={(value) => setAPIToken(value)}
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

interface CreateFlowdockNotification {
  org: string;
  repo: string;
  event: NotificationEvent;
  method: NotificationMethod;
  closeDrawer: () => void;
  setError: (error: string) => void;
}
