import {NotificationEvent} from 'src/hooks/UseEvents';
import {NotificationMethod} from 'src/hooks/UseNotificationMethods';
import {
  ActionGroup,
  Button,
  FormGroup,
  FormHelperText,
  HelperText,
  HelperTextItem,
  TextInput,
} from '@patternfly/react-core';
import {useEffect, useState} from 'react';
import {useUpdateNotifications} from 'src/hooks/UseUpdateNotifications';
import {NotificationEventConfig} from 'src/hooks/UseEvents';
import {ExclamationCircleIcon} from '@patternfly/react-icons';

export default function CreateHipchatNotification(
  props: CreateHipchatNotification,
) {
  const [roomId, setRoomId] = useState<string>('');
  const [token, setToken] = useState<string>('');
  const [title, setTitle] = useState<string>('');
  const {
    create,
    successCreatingNotification,
    errorCreatingNotification,
    resetCreatingNotification,
  } = useUpdateNotifications(props.org, props.repo);

  const createNotification = async () => {
    create({
      config: {
        notification_token: token,
        room_id: roomId,
      },
      event: props.event?.type,
      event_config: props.eventConfig,
      method: props.method?.type,
      title: title,
    });
  };

  const isValidRoomId = (roomId: string) => {
    const regex = /^[0-9]+$/;
    return regex.test(roomId);
  };

  const isFormComplete =
    props.method != undefined &&
    props.event != undefined &&
    token != '' &&
    roomId != '' &&
    props.isValidateConfig() &&
    isValidRoomId(roomId);

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
      <FormGroup fieldId="room-id-number" label="Room ID #" isRequired>
        <TextInput
          required
          id="room-id-number-field"
          value={roomId}
          onChange={(_event, value) => setRoomId(value)}
        />

        {!isValidRoomId(roomId) && (
          <FormHelperText>
            <HelperText>
              <HelperTextItem variant="error" icon={<ExclamationCircleIcon />}>
                Must be a number
              </HelperTextItem>
            </HelperText>
          </FormHelperText>
        )}
      </FormGroup>
      <FormGroup
        fieldId="room-notification-token"
        label="Room Notification Token"
        isRequired
      >
        <TextInput
          required
          id="room-notification-token-field"
          value={token}
          onChange={(_event, value) => setToken(value)}
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

interface CreateHipchatNotification {
  org: string;
  repo: string;
  event: NotificationEvent;
  method: NotificationMethod;
  eventConfig: NotificationEventConfig;
  isValidateConfig: () => boolean;
  closeDrawer: () => void;
  setError: (error: string) => void;
}
