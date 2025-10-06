import React, {useEffect} from 'react';
import {
  Button,
  Form,
  FormGroup,
  PageSection,
  PageSectionVariants,
} from '@patternfly/react-core';
import {useForm} from 'react-hook-form';
import {
  IOAuthApplication,
  useUpdateOAuthApplication,
} from 'src/hooks/UseOAuthApplications';
import {useAlerts} from 'src/hooks/UseAlerts';
import {AlertVariant} from 'src/atoms/AlertState';
import {FormTextInput} from 'src/components/forms/FormTextInput';
import {OAuthApplicationFormData} from '../types';

interface SettingsTabProps {
  application: IOAuthApplication | null;
  orgName: string;
  onSuccess: () => void;
}

export default function SettingsTab(props: SettingsTabProps) {
  const {addAlert} = useAlerts();

  const {
    control,
    handleSubmit,
    formState: {errors, isSubmitting, isDirty},
    reset,
  } = useForm<OAuthApplicationFormData>({
    defaultValues: {
      name: props.application?.name || '',
      application_uri: props.application?.application_uri || '',
      description: props.application?.description || '',
      avatar_email: props.application?.avatar_email || '',
      redirect_uri: props.application?.redirect_uri || '',
    },
    mode: 'onChange',
  });

  const {updateOAuthApplicationMutation} = useUpdateOAuthApplication(
    props.orgName,
    () => {
      // Success callback
      addAlert({
        variant: AlertVariant.Success,
        title: 'OAuth application updated successfully',
      });
      props.onSuccess();
    },
    () => {
      // Error callback
      addAlert({
        variant: AlertVariant.Failure,
        title: 'Failed to update OAuth application',
      });
    },
  );

  // Reset form when application changes
  useEffect(() => {
    if (props.application) {
      reset({
        name: props.application.name || '',
        application_uri: props.application.application_uri || '',
        description: props.application.description || '',
        avatar_email: props.application.avatar_email || '',
        redirect_uri: props.application.redirect_uri || '',
      });
    }
  }, [props.application, reset]);

  const onSubmit = (data: OAuthApplicationFormData) => {
    if (props.application?.client_id) {
      updateOAuthApplicationMutation({
        clientId: props.application.client_id,
        applicationData: data,
      });
    }
  };

  if (!props.application) {
    return <div>No application selected</div>;
  }

  return (
    <PageSection variant={PageSectionVariants.light}>
      <Form>
        <FormTextInput
          name="name"
          control={control}
          errors={errors}
          fieldId="app-name"
          label="Application Name"
          placeholder="Application Name"
          helperText="The name of the application that is displayed to users"
          required
          data-testid="application-name-input"
        />

        <FormTextInput
          name="application_uri"
          control={control}
          errors={errors}
          fieldId="app-uri"
          label="Homepage URL"
          placeholder="Homepage URL"
          helperText="The URL to which the application will link in the authorization view"
          data-testid="homepage-url-input"
        />

        <FormTextInput
          name="description"
          control={control}
          errors={errors}
          fieldId="app-description"
          label="Description"
          placeholder="Description"
          helperText="The user friendly description of the application"
          data-testid="description-input"
        />

        <FormTextInput
          name="avatar_email"
          control={control}
          errors={errors}
          fieldId="avatar-email"
          label="Avatar E-mail"
          placeholder="Avatar E-mail"
          helperText="An e-mail address representing the avatar for the application"
          data-testid="avatar-email-input"
        />

        <FormTextInput
          name="redirect_uri"
          control={control}
          errors={errors}
          fieldId="redirect-uri"
          label="Redirect/Callback URL Prefix"
          placeholder="OAuth Redirect URL"
          helperText="Allowed prefix for the application's OAuth redirection/callback URLs"
          data-testid="redirect-url-input"
        />

        <FormGroup>
          <Button
            variant="primary"
            onClick={handleSubmit(onSubmit)}
            isDisabled={isSubmitting || !isDirty}
            isLoading={isSubmitting}
            data-testid="update-application-button"
          >
            {isSubmitting ? 'Updating...' : 'Update Application'}
          </Button>
        </FormGroup>
      </Form>
    </PageSection>
  );
}
