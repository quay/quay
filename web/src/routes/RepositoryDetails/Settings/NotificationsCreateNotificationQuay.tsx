import {NotificationEvent} from 'src/hooks/UseEvents';
import {NotificationMethod} from 'src/hooks/UseNotificationMethods';
import {
  ActionGroup,
  Button,
  FormGroup,
  TextInput,
} from '@patternfly/react-core';
import {useEffect, useState} from 'react';
import EntitySearch from 'src/components/EntitySearch';
import {Entity} from 'src/resources/UserResource';
import {useUpdateNotifications} from 'src/hooks/UseUpdateNotifications';
import {NotificationEventConfig} from 'src/hooks/UseEvents';

export default function CreateQuayNotification(props: CreateQuayNotification) {
  const [title, setTitle] = useState<string>('');
  const [selectedEntity, setSelectedEntity] = useState<Entity>(null);
  const {
    create,
    successCreatingNotification,
    errorCreatingNotification,
    resetCreatingNotification,
  } = useUpdateNotifications(props.org, props.repo);

  const isFormComplete =
    props.method != undefined &&
    props.event != undefined &&
    props.isValidateConfig() &&
    selectedEntity != null;

  const createNotification = async () => {
    create({
      config: {
        target: selectedEntity,
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
      props.setError('Unable to create notification');
      resetCreatingNotification();
    }
  }, [errorCreatingNotification]);

  return (
    <>
      <FormGroup
        fieldId="quayNotificationRecipient"
        label="Recipient"
        isRequired
      >
        <EntitySearch
          org={props.org}
          onSelect={(e: Entity) => setSelectedEntity(e)}
          onError={() => props.setError('Unable to look up users')}
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

interface CreateQuayNotification {
  org: string;
  repo: string;
  event: NotificationEvent;
  method: NotificationMethod;
  eventConfig: NotificationEventConfig;
  isValidateConfig: () => boolean;
  closeDrawer: () => void;
  setError: (error: string) => void;
}
