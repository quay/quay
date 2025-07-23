import React, {useState} from 'react';
import {
  Button,
  Form,
  FormGroup,
  TextInput,
  ActionGroup,
  DrawerActions,
  DrawerCloseButton,
  DrawerHead,
  DrawerPanelBody,
  DrawerPanelContent,
} from '@patternfly/react-core';
import {useAlerts} from 'src/hooks/UseAlerts';
import {AlertVariant} from 'src/atoms/AlertState';
import {OrganizationDrawerContentType} from 'src/routes/OrganizationsList/Organization/Organization';
import {Ref} from 'react';
import {useCreateOAuthApplication} from 'src/hooks/UseOAuthApplications';
export default function CreateOAuthApplicationDrawer(
  props: CreateOAuthApplicationDrawerProps,
) {
  const [appName, setAppName] = useState('');
  const [homepageUrl, setHomepageUrl] = useState('');
  const [description, setDescription] = useState('');
  const [avatarEmail, setAvatarEmail] = useState('');
  const [redirectUrl, setRedirectUrl] = useState('');

  const {addAlert} = useAlerts();

  const handleCreateApplication = async () => {
    // Logic to handle application creation
    await createOAuthApplication({
      application_uri: homepageUrl,
      avatar_email: avatarEmail,
      description,
      name: appName,
      redirect_uri: redirectUrl,
    });
  };

  const {createOAuthApplication} = useCreateOAuthApplication(props.orgName, {
    onError: (error) => {
      const errorMessage =
        error?.error?.message || error?.message || String(error);
      addAlert({
        variant: AlertVariant.Failure,
        title: 'Error creating application',
        message: errorMessage,
      });
    },
    onSuccess: () => {
      addAlert({
        variant: AlertVariant.Success,
        title: `Successfully created application: ${appName}`,
      });
      props.closeDrawer();
    },
  });

  return (
    <DrawerPanelContent>
      <DrawerHead>
        <h2>Create application</h2>
        <DrawerActions>
          <DrawerCloseButton onClick={props.closeDrawer} />
        </DrawerActions>
      </DrawerHead>
      <DrawerPanelBody>
        <Form>
          <FormGroup label="Application Name" isRequired fieldId="app-name">
            <TextInput
              isRequired
              type="text"
              id="app-name"
              name="app-name"
              value={appName}
              onChange={(_event, value) => setAppName(value)}
              aria-label="Application Name"
            />
          </FormGroup>
          <FormGroup label="Homepage URL" fieldId="homepage-url">
            <TextInput
              type="url"
              id="homepage-url"
              name="homepage-url"
              value={homepageUrl}
              onChange={(_event, value) => setHomepageUrl(value)}
              aria-label="Homepage URL"
            />
          </FormGroup>
          <FormGroup label="Description" fieldId="description">
            <TextInput
              type="text"
              id="description"
              name="description"
              value={description}
              onChange={(_event, value) => setDescription(value)}
              aria-label="Description"
            />
          </FormGroup>
          <FormGroup label="Avatar e-mail" fieldId="avatar-email">
            <TextInput
              type="email"
              id="avatar-email"
              name="avatar-email"
              value={avatarEmail}
              onChange={(_event, value) => setAvatarEmail(value)}
              aria-label="Avatar e-mail"
            />
          </FormGroup>
          <FormGroup
            label="Redirect/Callback URL prefix"
            fieldId="redirect-url"
          >
            <TextInput
              type="url"
              id="redirect-url"
              name="redirect-url"
              value={redirectUrl}
              onChange={(_event, value) => setRedirectUrl(value)}
              aria-label="Redirect/Callback URL prefix"
            />
          </FormGroup>
          <ActionGroup>
            <Button
              variant="primary"
              isDisabled={!appName}
              onClick={handleCreateApplication}
            >
              Create application
            </Button>
          </ActionGroup>
        </Form>
      </DrawerPanelBody>
    </DrawerPanelContent>
  );
}

interface CreateOAuthApplicationDrawerProps {
  orgName: string;
  closeDrawer: () => void;
  drawerRef: Ref<HTMLDivElement>;
  drawerContent: OrganizationDrawerContentType;
}
