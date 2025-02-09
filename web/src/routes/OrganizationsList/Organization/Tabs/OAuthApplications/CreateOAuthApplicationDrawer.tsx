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
      addAlert({
        variant: AlertVariant.Failure,
        title: 'Error creating application',
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
              onChange={(value) => setAppName(value.target.value)}
              aria-label="Application Name"
            />
          </FormGroup>
          <FormGroup label="Homepage URL" isRequired fieldId="homepage-url">
            <TextInput
              isRequired
              type="url"
              id="homepage-url"
              name="homepage-url"
              value={homepageUrl}
              onChange={(value) => setHomepageUrl(value.target.value)}
              aria-label="Homepage URL"
            />
          </FormGroup>
          <FormGroup label="Description" fieldId="description">
            <TextInput
              type="text"
              id="description"
              name="description"
              value={description}
              onChange={(value) => setDescription(value.target.value)}
              aria-label="Description"
            />
          </FormGroup>
          <FormGroup label="Avatar e-mail" fieldId="avatar-email">
            <TextInput
              type="email"
              id="avatar-email"
              name="avatar-email"
              value={avatarEmail}
              onChange={(value) => setAvatarEmail(value.target.value)}
              aria-label="Avatar e-mail"
            />
          </FormGroup>
          <FormGroup
            label="Redirect/Callback URL prefix"
            isRequired
            fieldId="redirect-url"
          >
            <TextInput
              isRequired
              type="url"
              id="redirect-url"
              name="redirect-url"
              value={redirectUrl}
              onChange={(value) => setRedirectUrl(value.target.value)}
              aria-label="Redirect/Callback URL prefix"
            />
          </FormGroup>
          <ActionGroup>
            <Button
              variant="primary"
              isDisabled={!appName || !homepageUrl || !redirectUrl}
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
