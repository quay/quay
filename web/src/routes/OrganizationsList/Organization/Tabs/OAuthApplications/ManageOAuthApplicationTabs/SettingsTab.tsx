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
          placeholder="My OAuth Application"
          helperText="A user-readable name for this application"
          required
        />

        <FormTextInput
          name="application_uri"
          control={control}
          errors={errors}
          fieldId="app-uri"
          label="Homepage URL"
          placeholder="https://myapp.example.com"
          helperText="The URL where users can find more information about your application"
        />

        <FormTextInput
          name="description"
          control={control}
          errors={errors}
          fieldId="app-description"
          label="Application Description"
          placeholder="Description of my OAuth application"
          helperText="An optional description for this application"
        />

        <FormTextInput
          name="avatar_email"
          control={control}
          errors={errors}
          fieldId="avatar-email"
          label="Avatar E-mail"
          placeholder="user@example.com"
          helperText="E-mail address for the application avatar"
        />

        <FormTextInput
          name="redirect_uri"
          control={control}
          errors={errors}
          fieldId="redirect-uri"
          label="Authorization Callback URL"
          placeholder="https://myapp.example.com/oauth/callback"
          helperText="The callback URL to redirect users after authorization"
        />

        <FormGroup>
          <Button
            variant="primary"
            onClick={handleSubmit(onSubmit)}
            isDisabled={isSubmitting || !isDirty}
            isLoading={isSubmitting}
          >
            {isSubmitting ? 'Updating...' : 'Update Application'}
          </Button>
        </FormGroup>
      </Form>
    </PageSection>
  );
}
