import {
  Alert,
  AlertActionCloseButton,
  Dropdown,
  DropdownItem,
  DropdownToggle,
  Form,
  FormGroup,
  Title,
} from '@patternfly/react-core';
import {useState} from 'react';
import './NotificationsCreateNotification.css';
import Conditional from 'src/components/empty/Conditional';
import {NotificationEvent, useEvents} from 'src/hooks/UseEvents';
import {
  NotificationMethod,
  useNotificationMethods,
} from 'src/hooks/UseNotificationMethods';
import {NotificationMethodType} from 'src/resources/NotificationResource';
import CreateEmailNotification from './NotificationsCreateNotificationEmail';
import CreateFlowdockNotification from './NotificationsCreateNotificationFlowdock';
import CreateHipchatNotification from './NotificationsCreateNotificationHipchat';
import CreateQuayNotification from './NotificationsCreateNotificationQuay';
import CreateSlackNotification from './NotificationsCreateNotificationSlack';
import CreateWebhookNotification from './NotificationsCreateNotificationWebhook';

export default function CreateNotification(props: CreateNotificationProps) {
  const [isEventOpen, setIsEventOpen] = useState<boolean>();
  const [isMethodOpen, setIsMethodOpen] = useState<boolean>();
  const [event, setEvent] = useState<NotificationEvent>();
  const [method, setMethod] = useState<NotificationMethod>();
  const {events} = useEvents();
  const {notificationMethods} = useNotificationMethods();
  const [error, setError] = useState<string>('');

  return (
    <>
      <Title headingLevel="h3">Create Notification</Title>
      <Form id="create-notification-form">
        <Conditional if={error != ''}>
          <Alert
            isInline
            actionClose={
              <AlertActionCloseButton onClose={() => setError('')} />
            }
            variant="danger"
            title={error}
          />
        </Conditional>
        <FormGroup fieldId="event" label="When this event occurs" isRequired>
          <Dropdown
            className="create-notification-dropdown"
            required
            onSelect={() => setIsEventOpen(false)}
            toggle={
              <DropdownToggle onToggle={(isOpen) => setIsEventOpen(isOpen)}>
                {event?.title ? event?.title : 'Select event...'}
              </DropdownToggle>
            }
            isOpen={isEventOpen}
            dropdownItems={events.map((event) => (
              <Conditional key={event.type} if={event.enabled}>
                <DropdownItem onClick={() => setEvent(event)}>
                  {event.icon} {event.title}
                </DropdownItem>
              </Conditional>
            ))}
          />
        </FormGroup>
        <FormGroup
          fieldId="method"
          label="Then issue a notification"
          isRequired
        >
          <Dropdown
            className="create-notification-dropdown"
            onSelect={() => setIsMethodOpen(false)}
            toggle={
              <DropdownToggle onToggle={(isOpen) => setIsMethodOpen(isOpen)}>
                {method?.title ? method?.title : 'Select method...'}
              </DropdownToggle>
            }
            isOpen={isMethodOpen}
            dropdownItems={notificationMethods.map((method) => (
              <Conditional key={method.type} if={method.enabled}>
                <DropdownItem onClick={() => setMethod(method)}>
                  {method.title}
                </DropdownItem>
              </Conditional>
            ))}
          />
        </FormGroup>
        <Conditional if={method?.type == NotificationMethodType.email}>
          <CreateEmailNotification
            org={props.org}
            repo={props.repo}
            event={event}
            method={method}
            closeDrawer={props.closeDrawer}
            setError={setError}
          />
        </Conditional>
        <Conditional
          if={method?.type == NotificationMethodType.quaynotification}
        >
          <CreateQuayNotification
            org={props.org}
            repo={props.repo}
            event={event}
            method={method}
            closeDrawer={props.closeDrawer}
            setError={setError}
          />
        </Conditional>
        <Conditional if={method?.type == NotificationMethodType.flowdock}>
          <CreateFlowdockNotification
            org={props.org}
            repo={props.repo}
            event={event}
            method={method}
            closeDrawer={props.closeDrawer}
            setError={setError}
          />
        </Conditional>
        <Conditional if={method?.type == NotificationMethodType.hipchat}>
          <CreateHipchatNotification
            org={props.org}
            repo={props.repo}
            event={event}
            method={method}
            closeDrawer={props.closeDrawer}
            setError={setError}
          />
        </Conditional>
        <Conditional if={method?.type == NotificationMethodType.slack}>
          <CreateSlackNotification
            org={props.org}
            repo={props.repo}
            event={event}
            method={method}
            closeDrawer={props.closeDrawer}
            setError={setError}
          />
        </Conditional>
        <Conditional if={method?.type == NotificationMethodType.webhook}>
          <CreateWebhookNotification
            org={props.org}
            repo={props.repo}
            event={event}
            method={method}
            closeDrawer={props.closeDrawer}
            setError={setError}
          />
        </Conditional>
      </Form>
    </>
  );
}

interface CreateNotificationProps {
  org: string;
  repo: string;
  closeDrawer: () => void;
}
