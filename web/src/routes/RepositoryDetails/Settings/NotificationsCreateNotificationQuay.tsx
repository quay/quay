import {NotificationEvent} from 'src/hooks/UseEvents';
import {NotificationMethod} from 'src/hooks/UseNotificationMethods';
import {
  ActionGroup,
  Button,
  Divider,
  FormGroup,
  SelectGroup,
  SelectOption,
  TextInput,
} from '@patternfly/react-core';
import {UsersIcon} from '@patternfly/react-icons';
import {useEffect, useState} from 'react';
import React from 'react';
import EntitySearch from 'src/components/EntitySearch';
import {Entity, EntityKind} from 'src/resources/UserResource';
import {useUpdateNotifications} from 'src/hooks/UseUpdateNotifications';
import {NotificationEventConfig} from 'src/hooks/UseEvents';
import {useFetchTeams} from 'src/hooks/UseTeams';
import Conditional from 'src/components/empty/Conditional';
import {useOrganizations} from 'src/hooks/UseOrganizations';

export default function CreateQuayNotification(props: CreateQuayNotification) {
  const [title, setTitle] = useState<string>('');
  const [selectedEntity, setSelectedEntity] = useState<Entity>(null);
  const {usernames} = useOrganizations();
  const isUserOrganization = usernames.includes(props.org);
  const {teams} = useFetchTeams(props.org);
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

  const handleTeamSelect = (teamName: string) => {
    setSelectedEntity({
      name: teamName,
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
          onClick={() => props.openCreateTeamModal()}
          isFocused
        >
          <UsersIcon /> &nbsp; Create team
        </SelectOption>
      </Conditional>
    </React.Fragment>,
  ];

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
          defaultOptions={defaultOptions}
          onTeamSelect={handleTeamSelect}
          value={selectedEntity?.name}
          onClear={() => setSelectedEntity(null)}
          placeholderText="Search for user"
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
  openCreateTeamModal: () => void;
}
