import React from 'react';
import {Modal, ModalVariant, Button, Form} from '@patternfly/react-core';
import {useAlerts} from 'src/hooks/UseAlerts';
import {FormTextInput} from 'src/components/forms/FormTextInput';
import {useOAuthApplicationForm} from 'src/hooks/UseOAuthApplicationForm';
import {OAuthApplicationFormData} from './types';

export default function CreateOAuthApplicationModal(
  props: CreateOAuthApplicationModalProps,
) {
  const {addAlert} = useAlerts();

  const {control, errors, formValues, handleSubmit, isValid} =
    useOAuthApplicationForm(
      props.orgName,
      addAlert,
      props.handleModalToggle, // Close modal on success
    );

  return (
    <Modal
      variant={ModalVariant.medium}
      title="Create OAuth application"
      isOpen={props.isModalOpen}
      onClose={props.handleModalToggle}
      data-testid="create-oauth-modal"
      actions={[
        <Button
          key="create"
          variant="primary"
          type="submit"
          form="create-oauth-form"
          isDisabled={!isValid || !formValues.name}
          data-testid="create-oauth-submit"
        >
          Create application
        </Button>,
        <Button key="cancel" variant="link" onClick={props.handleModalToggle}>
          Cancel
        </Button>,
      ]}
    >
      <Form id="create-oauth-form" onSubmit={handleSubmit}>
        <FormTextInput<OAuthApplicationFormData>
          name="name"
          control={control}
          errors={errors}
          label="Application Name"
          placeholder="Application Name"
          required
          fieldId="app-name"
          helperText="The name of the application that is displayed to users"
          data-testid="application-name-input"
        />

        <FormTextInput<OAuthApplicationFormData>
          name="application_uri"
          control={control}
          errors={errors}
          label="Homepage URL"
          placeholder="Homepage URL"
          type="text"
          fieldId="homepage-url"
          helperText="The URL to which the application will link in the authorization view"
          data-testid="homepage-url-input"
        />

        <FormTextInput<OAuthApplicationFormData>
          name="description"
          control={control}
          errors={errors}
          label="Description"
          placeholder="Description"
          fieldId="description"
          helperText="The user friendly description of the application"
          data-testid="description-input"
        />

        <FormTextInput<OAuthApplicationFormData>
          name="avatar_email"
          control={control}
          errors={errors}
          label="Avatar E-mail"
          placeholder="Avatar E-mail"
          type="email"
          fieldId="avatar-email"
          helperText="An e-mail address representing the avatar for the application"
          data-testid="avatar-email-input"
        />

        <FormTextInput<OAuthApplicationFormData>
          name="redirect_uri"
          control={control}
          errors={errors}
          label="Redirect/Callback URL prefix"
          placeholder="OAuth Redirect URL"
          type="text"
          fieldId="redirect-url"
          helperText="Allowed prefix for the application's OAuth redirection/callback URLs"
          data-testid="redirect-url-input"
        />
      </Form>
    </Modal>
  );
}

interface CreateOAuthApplicationModalProps {
  orgName: string;
  isModalOpen: boolean;
  handleModalToggle: () => void;
}
