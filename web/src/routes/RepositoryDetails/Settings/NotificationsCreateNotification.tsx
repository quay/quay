import {useState} from 'react';
import {
  Alert,
  AlertActionCloseButton,
  Dropdown,
  DropdownItem,
  DropdownList,
  Form,
  FormGroup,
  MenuToggle,
  MenuToggleElement,
  Title,
} from '@patternfly/react-core';
import './NotificationsCreateNotification.css';
import Conditional from 'src/components/empty/Conditional';
import {
  NotificationEvent,
  NotificationEventConfig,
  useEvents,
} from 'src/hooks/UseEvents';
import {
  NotificationMethod,
  useNotificationMethods,
} from 'src/hooks/UseNotificationMethods';
import {
  NotificationEventType,
  NotificationMethodType,
} from 'src/resources/NotificationResource';
import CreateEmailNotification from './NotificationsCreateNotificationEmail';
import CreateFlowdockNotification from './NotificationsCreateNotificationFlowdock';
import CreateHipchatNotification from './NotificationsCreateNotificationHipchat';
import CreateQuayNotification from './NotificationsCreateNotificationQuay';
import CreateSlackNotification from './NotificationsCreateNotificationSlack';
import CreateWebhookNotification from './NotificationsCreateNotificationWebhook';
import RepoEventExpiry from './RepoEventExpiry';
import {CreateTeamModal} from 'src/routes/OrganizationsList/Organization/Tabs/DefaultPermissions/createPermissionDrawer/CreateTeamModal';

export default function CreateNotification(props: CreateNotificationProps) {
  const [isEventOpen, setIsEventOpen] = useState(false);
  const [isMethodOpen, setIsMethodOpen] = useState(false);
  const [event, setEvent] = useState<NotificationEvent>();
  const [method, setMethod] = useState<NotificationMethod>();
  const [eventConfig, setEventConfig] = useState<NotificationEventConfig>({});
  const {events} = useEvents();
  const {notificationMethods} = useNotificationMethods();
  const [error, setError] = useState<string>('');
  const [isTeamModalOpen, setIsTeamModalOpen] = useState(false);
  const [teamName, setTeamName] = useState('');
  const [teamDescription, setTeamDescription] = useState('');

  const isValidateConfig = () => {
    if (event?.type == NotificationEventType.imageExpiry) {
      return eventConfig?.days != undefined && eventConfig?.days > 0;
    }
    return true;
  };

  const validateTeamName = (name: string) => {
    const teamNameRegex = /^[a-z0-9_]{2,255}$/;
    return teamNameRegex.test(name);
  };

  return (
    <>
      <Title headingLevel="h3">Create notification</Title>
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
            onSelect={() => setIsEventOpen(false)}
            toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
              <MenuToggle
                ref={toggleRef}
                id="event-dropdown-toggle"
                onClick={() => setIsEventOpen(() => !isEventOpen)}
                isExpanded={isEventOpen}
              >
                {event?.title ? event?.title : 'Select event...'}
              </MenuToggle>
            )}
            isOpen={isEventOpen}
            onOpenChange={(isOpen) => setIsEventOpen(isOpen)}
            shouldFocusToggleOnSelect
          >
            <DropdownList>
              {events.map((event) => (
                <Conditional key={event.type} if={event.enabled}>
                  <DropdownItem onClick={() => setEvent(event)}>
                    {event.icon} {event.title}
                  </DropdownItem>
                </Conditional>
              ))}
            </DropdownList>
          </Dropdown>
        </FormGroup>
        <Conditional if={event?.type == NotificationEventType.imageExpiry}>
          <RepoEventExpiry
            eventConfig={eventConfig}
            setEventConfig={setEventConfig}
          />
        </Conditional>
        <FormGroup
          fieldId="method"
          label="Then issue a notification"
          isRequired
        >
          <Dropdown
            className="create-notification-dropdown"
            onSelect={() => setIsMethodOpen(false)}
            toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
              <MenuToggle
                ref={toggleRef}
                id="method-dropdown-toggle"
                onClick={() => setIsMethodOpen(() => !isMethodOpen)}
                isExpanded={isMethodOpen}
              >
                {method?.title ? method?.title : 'Select method...'}
              </MenuToggle>
            )}
            isOpen={isMethodOpen}
            onOpenChange={(isOpen) => setIsMethodOpen(isOpen)}
            shouldFocusToggleOnSelect
          >
            <DropdownList>
              {notificationMethods.map((method) => (
                <Conditional key={method.type} if={method.enabled}>
                  <DropdownItem onClick={() => setMethod(method)}>
                    {method.title}
                  </DropdownItem>
                </Conditional>
              ))}
            </DropdownList>
          </Dropdown>
        </FormGroup>
        <Conditional if={method?.type == NotificationMethodType.email}>
          <CreateEmailNotification
            org={props.org}
            repo={props.repo}
            event={event}
            method={method}
            eventConfig={eventConfig}
            isValidateConfig={isValidateConfig}
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
            eventConfig={eventConfig}
            isValidateConfig={isValidateConfig}
            closeDrawer={props.closeDrawer}
            setError={setError}
            openCreateTeamModal={() => setIsTeamModalOpen(true)}
          />
        </Conditional>
        <Conditional if={method?.type == NotificationMethodType.flowdock}>
          <CreateFlowdockNotification
            org={props.org}
            repo={props.repo}
            event={event}
            method={method}
            eventConfig={eventConfig}
            isValidateConfig={isValidateConfig}
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
            eventConfig={eventConfig}
            isValidateConfig={isValidateConfig}
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
            eventConfig={eventConfig}
            isValidateConfig={isValidateConfig}
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
            eventConfig={eventConfig}
            isValidateConfig={isValidateConfig}
            closeDrawer={props.closeDrawer}
            setError={setError}
          />
        </Conditional>
      </Form>
      <CreateTeamModal
        orgName={props.org}
        isModalOpen={isTeamModalOpen}
        handleModalToggle={() => setIsTeamModalOpen(!isTeamModalOpen)}
        teamName={teamName}
        setTeamName={setTeamName}
        description={teamDescription}
        setDescription={setTeamDescription}
        nameLabel="Team name"
        descriptionLabel="Team description"
        helperText="Enter a description for the team"
        nameHelperText="Enter a unique team name (lowercase letters, numbers, and underscores only)"
        validateName={validateTeamName}
      />
    </>
  );
}

interface CreateNotificationProps {
  org: string;
  repo: string;
  closeDrawer: () => void;
}
