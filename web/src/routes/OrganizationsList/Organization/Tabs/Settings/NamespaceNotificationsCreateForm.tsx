import {useEffect, useState} from 'react';
import React from 'react';
import {
  ActionGroup,
  Alert,
  AlertActionCloseButton,
  Button,
  Divider,
  Dropdown,
  DropdownItem,
  DropdownList,
  Form,
  FormGroup,
  FormHelperText,
  HelperText,
  HelperTextItem,
  MenuToggle,
  MenuToggleElement,
  Modal,
  ModalBody,
  ModalHeader,
  ModalVariant,
  SelectGroup,
  SelectOption,
  TextArea,
  TextInput,
} from '@patternfly/react-core';
import {ExclamationCircleIcon, UsersIcon} from '@patternfly/react-icons';
import Conditional from 'src/components/empty/Conditional';
import EntitySearch from 'src/components/EntitySearch';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {useUpdateNamespaceNotifications} from 'src/hooks/UseUpdateNamespaceNotifications';
import {useFetchTeams} from 'src/hooks/UseTeams';
import {useOrganizations} from 'src/hooks/UseOrganizations';
import {isValidEmail} from 'src/libs/utils';
import {Entity, EntityKind} from 'src/resources/UserResource';
import {
  NamespaceNotificationEventType,
  NamespaceNotificationMethodType,
} from 'src/resources/NamespaceNotificationResource';
import {CreateTeamModal} from 'src/routes/OrganizationsList/Organization/Tabs/DefaultPermissions/createPermissionDrawer/CreateTeamModal';

interface NotificationEventOption {
  type: NamespaceNotificationEventType;
  title: string;
}

interface NotificationMethodOption {
  type: NamespaceNotificationMethodType;
  title: string;
  enabled: boolean;
}

const NAMESPACE_EVENTS: NotificationEventOption[] = [
  {type: NamespaceNotificationEventType.quotaWarning, title: 'Quota Warning'},
  {type: NamespaceNotificationEventType.quotaError, title: 'Quota Error'},
];

export default function NamespaceNotificationsCreateForm(
  props: NamespaceNotificationsCreateFormProps,
) {
  const config = useQuayConfig();
  const [isEventOpen, setIsEventOpen] = useState(false);
  const [isMethodOpen, setIsMethodOpen] = useState(false);
  const [event, setEvent] = useState<NotificationEventOption>(null);
  const [method, setMethod] = useState<NotificationMethodOption>(null);
  const [title, setTitle] = useState('');
  const [error, setError] = useState('');

  const [email, setEmail] = useState('');
  const [slackUrl, setSlackUrl] = useState('');
  const [webhookUrl, setWebhookUrl] = useState('');
  const [webhookTemplate, setWebhookTemplate] = useState('');
  const [selectedEntity, setSelectedEntity] = useState<Entity>(null);

  const [isTeamModalOpen, setIsTeamModalOpen] = useState(false);
  const [teamName, setTeamName] = useState('');
  const [teamDescription, setTeamDescription] = useState('');

  const {usernames} = useOrganizations();
  const isUserOrganization = usernames.includes(props.orgname);
  const {teams} = useFetchTeams(props.orgname);

  const {
    create,
    successCreatingNotification,
    errorCreatingNotification,
    resetCreatingNotification,
  } = useUpdateNamespaceNotifications(props.orgname, props.isUser);

  const NAMESPACE_METHODS: NotificationMethodOption[] = [
    {
      type: NamespaceNotificationMethodType.email,
      title: 'Email Notification',
      enabled: !!config?.features?.MAILING,
    },
    {
      type: NamespaceNotificationMethodType.quaynotification,
      title: `${config?.config?.REGISTRY_TITLE_SHORT || 'Quay'} Notification`,
      enabled: true,
    },
    {
      type: NamespaceNotificationMethodType.slack,
      title: 'Slack Notification',
      enabled: true,
    },
    {
      type: NamespaceNotificationMethodType.webhook,
      title: 'Webhook POST',
      enabled: true,
    },
  ];

  const isValidSlackUrl = (url: string): boolean => {
    const regex =
      /^https:\/\/hooks\.slack\.com\/services\/[A-Z0-9]+\/[A-Z0-9]+\/[a-zA-Z0-9]+$/;
    return regex.test(url);
  };

  const isValidUrl = (url: string): boolean => {
    return url.startsWith('http://') || url.startsWith('https://');
  };

  const isFormComplete = (): boolean => {
    if (!event || !method) return false;
    switch (method.type) {
      case NamespaceNotificationMethodType.email:
        return email !== '' && isValidEmail(email);
      case NamespaceNotificationMethodType.slack:
        return slackUrl !== '' && isValidSlackUrl(slackUrl);
      case NamespaceNotificationMethodType.webhook:
        return webhookUrl !== '' && isValidUrl(webhookUrl);
      case NamespaceNotificationMethodType.quaynotification:
        return selectedEntity != null;
      default:
        return false;
    }
  };

  const getConfig = (): Record<string, unknown> => {
    switch (method?.type) {
      case NamespaceNotificationMethodType.email:
        return {email};
      case NamespaceNotificationMethodType.slack:
        return {url: slackUrl};
      case NamespaceNotificationMethodType.webhook:
        return {url: webhookUrl, template: webhookTemplate};
      case NamespaceNotificationMethodType.quaynotification:
        return {target: selectedEntity};
      default:
        return {};
    }
  };

  const handleSubmit = () => {
    create({
      config: getConfig(),
      event: event.type,
      event_config: {},
      method: method.type,
      title,
    });
  };

  useEffect(() => {
    if (successCreatingNotification) {
      resetCreatingNotification();
      props.onClose();
    }
  }, [successCreatingNotification]);

  useEffect(() => {
    if (errorCreatingNotification) {
      setError(errorCreatingNotification);
      resetCreatingNotification();
    }
  }, [errorCreatingNotification]);

  const validateTeamName = (name: string): boolean => {
    const teamNameRegex = /^[a-z0-9_]{2,255}$/;
    return teamNameRegex.test(name);
  };

  const handleTeamSelect = (name: string) => {
    setSelectedEntity({
      name,
      is_robot: false,
      kind: EntityKind.team,
    });
  };

  const defaultOptions = [
    <React.Fragment key="default-options">
      <Conditional if={!isUserOrganization && teams?.length > 0}>
        <SelectGroup label="Teams" key="teams-group">
          {teams?.map(({name}) => (
            <SelectOption data-testid={`${name}-team`} key={name} value={name}>
              {name}
            </SelectOption>
          ))}
        </SelectGroup>
        <Divider component="li" key="divider-1" />
      </Conditional>
      <Conditional if={!isUserOrganization}>
        <SelectOption
          data-testid="create-new-team-btn"
          key="create-team"
          component="button"
          onClick={() => setIsTeamModalOpen(true)}
          isFocused
        >
          <UsersIcon /> &nbsp; Create team
        </SelectOption>
      </Conditional>
    </React.Fragment>,
  ];

  return (
    <>
      <Modal
        variant={ModalVariant.medium}
        isOpen={props.isOpen}
        onClose={props.onClose}
      >
        <ModalHeader title="Create notification" />
        <ModalBody>
          <Form id="create-ns-notification-form">
            <Conditional if={error !== ''}>
              <Alert
                isInline
                actionClose={
                  <AlertActionCloseButton onClose={() => setError('')} />
                }
                variant="danger"
                title={error}
              />
            </Conditional>

            <FormGroup
              fieldId="ns-notification-event"
              label="When this event occurs"
              isRequired
            >
              <Dropdown
                onSelect={() => setIsEventOpen(false)}
                toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
                  <MenuToggle
                    ref={toggleRef}
                    id="ns-event-dropdown-toggle"
                    data-testid="ns-notification-event-dropdown"
                    onClick={() => setIsEventOpen((prev) => !prev)}
                    isExpanded={isEventOpen}
                    isFullWidth
                  >
                    {event?.title ?? 'Select event...'}
                  </MenuToggle>
                )}
                isOpen={isEventOpen}
                onOpenChange={setIsEventOpen}
                shouldFocusToggleOnSelect
              >
                <DropdownList>
                  {NAMESPACE_EVENTS.map((e) => (
                    <DropdownItem
                      key={e.type}
                      data-testid={`ns-event-${e.type}`}
                      onClick={() => setEvent(e)}
                    >
                      {e.title}
                    </DropdownItem>
                  ))}
                </DropdownList>
              </Dropdown>
            </FormGroup>

            <FormGroup
              fieldId="ns-notification-method"
              label="Then issue a notification"
              isRequired
            >
              <Dropdown
                onSelect={() => setIsMethodOpen(false)}
                toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
                  <MenuToggle
                    ref={toggleRef}
                    id="ns-method-dropdown-toggle"
                    data-testid="ns-notification-method-dropdown"
                    onClick={() => setIsMethodOpen((prev) => !prev)}
                    isExpanded={isMethodOpen}
                    isFullWidth
                  >
                    {method?.title ?? 'Select method...'}
                  </MenuToggle>
                )}
                isOpen={isMethodOpen}
                onOpenChange={setIsMethodOpen}
                shouldFocusToggleOnSelect
              >
                <DropdownList>
                  {NAMESPACE_METHODS.filter((m) => m.enabled).map((m) => (
                    <DropdownItem
                      key={m.type}
                      data-testid={`ns-method-${m.type}`}
                      onClick={() => setMethod(m)}
                    >
                      {m.title}
                    </DropdownItem>
                  ))}
                </DropdownList>
              </Dropdown>
            </FormGroup>

            <Conditional
              if={method?.type === NamespaceNotificationMethodType.email}
            >
              <FormGroup
                fieldId="ns-notification-email"
                label="E-mail address"
                isRequired
              >
                <TextInput
                  id="ns-notification-email"
                  data-testid="ns-notification-email"
                  isRequired
                  value={email}
                  onChange={(_event, value) => setEmail(value)}
                />
                {email !== '' && !isValidEmail(email) && (
                  <FormHelperText>
                    <HelperText>
                      <HelperTextItem
                        variant="error"
                        icon={<ExclamationCircleIcon />}
                      >
                        Invalid email
                      </HelperTextItem>
                    </HelperText>
                  </FormHelperText>
                )}
              </FormGroup>
            </Conditional>

            <Conditional
              if={method?.type === NamespaceNotificationMethodType.slack}
            >
              <FormGroup
                fieldId="ns-notification-slack-url"
                label="Webhook URL"
                isRequired
              >
                <TextInput
                  id="ns-notification-slack-url"
                  data-testid="ns-notification-slack-url"
                  isRequired
                  value={slackUrl}
                  onChange={(_event, value) => setSlackUrl(value)}
                />
                {slackUrl !== '' && !isValidSlackUrl(slackUrl) && (
                  <FormHelperText>
                    <HelperText>
                      <HelperTextItem
                        variant="error"
                        icon={<ExclamationCircleIcon />}
                      >
                        Must be a valid Slack webhook URL
                      </HelperTextItem>
                    </HelperText>
                  </FormHelperText>
                )}
              </FormGroup>
            </Conditional>

            <Conditional
              if={method?.type === NamespaceNotificationMethodType.webhook}
            >
              <FormGroup
                fieldId="ns-notification-webhook-url"
                label="Webhook URL"
                isRequired
              >
                <TextInput
                  id="ns-notification-webhook-url"
                  data-testid="ns-notification-webhook-url"
                  isRequired
                  value={webhookUrl}
                  onChange={(_event, value) => setWebhookUrl(value)}
                />
                {webhookUrl !== '' && !isValidUrl(webhookUrl) && (
                  <FormHelperText>
                    <HelperText>
                      <HelperTextItem
                        variant="error"
                        icon={<ExclamationCircleIcon />}
                      >
                        URL must begin with http(s)://
                      </HelperTextItem>
                    </HelperText>
                  </FormHelperText>
                )}
              </FormGroup>
              <FormGroup
                fieldId="ns-notification-webhook-template"
                label="POST JSON body template"
              >
                <TextArea
                  id="ns-notification-webhook-template"
                  data-testid="ns-notification-webhook-template"
                  value={webhookTemplate}
                  onChange={(_event, value) => setWebhookTemplate(value)}
                />
              </FormGroup>
            </Conditional>

            <Conditional
              if={
                method?.type ===
                NamespaceNotificationMethodType.quaynotification
              }
            >
              <FormGroup
                fieldId="ns-notification-recipient"
                label="Recipient"
                isRequired
              >
                <EntitySearch
                  org={props.orgname}
                  onSelect={(e: Entity) => setSelectedEntity(e)}
                  onError={() => setError('Unable to look up users')}
                  defaultOptions={defaultOptions}
                  onTeamSelect={handleTeamSelect}
                  value={selectedEntity?.name}
                  onClear={() => setSelectedEntity(null)}
                  placeholderText="Search for user"
                />
              </FormGroup>
            </Conditional>

            <FormGroup fieldId="ns-notification-title" label="Title">
              <TextInput
                id="ns-notification-title"
                data-testid="ns-notification-title"
                value={title}
                onChange={(_event, value) => setTitle(value)}
              />
            </FormGroup>

            <ActionGroup>
              <Button
                data-testid="ns-notification-submit-btn"
                isDisabled={!isFormComplete()}
                onClick={handleSubmit}
                variant="primary"
              >
                Submit
              </Button>
              <Button variant="link" onClick={props.onClose}>
                Cancel
              </Button>
            </ActionGroup>
          </Form>
        </ModalBody>
      </Modal>
      <CreateTeamModal
        orgName={props.orgname}
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

interface NamespaceNotificationsCreateFormProps {
  orgname: string;
  isUser?: boolean;
  isOpen: boolean;
  onClose: () => void;
}
