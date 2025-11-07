import React from 'react';
import {Controller} from 'react-hook-form';
import {
  Modal,
  ModalVariant,
  Form,
  FormGroup,
  TextInput,
  TextArea,
  Button,
  HelperText,
  HelperTextItem,
} from '@patternfly/react-core';
import {useCreateServiceKey} from 'src/hooks/UseCreateServiceKey';
import {useUI} from 'src/contexts/UIContext';
import FormError from 'src/components/errors/FormError';

interface CreateServiceKeyFormProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const CreateServiceKeyForm: React.FC<CreateServiceKeyFormProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const {addAlert} = useUI();
  const [error, setError] = React.useState<string | null>(null);

  const formHook = useCreateServiceKey(addAlert, setError, () => {
    onSuccess();
    onClose();
  });

  const handleClose = () => {
    formHook.reset();
    setError(null);
    onClose();
  };

  return (
    <Modal
      variant={ModalVariant.medium}
      title="Create Preshareable Service Key"
      isOpen={isOpen}
      onClose={handleClose}
      data-testid="create-service-key-modal"
      actions={[
        <Button
          key="create"
          variant="primary"
          data-testid="create-key-submit"
          onClick={formHook.handleSubmit(formHook.onSubmit)}
          isLoading={formHook.isSubmitting}
          isDisabled={!formHook.isValid || formHook.isSubmitting}
        >
          Create Key
        </Button>,
        <Button key="cancel" variant="link" onClick={handleClose}>
          Cancel
        </Button>,
      ]}
    >
      <Form>
        {error && <FormError message={error} setErr={setError} />}

        <FormGroup label="Key Name:" fieldId="key-name" isRequired>
          <Controller
            name="name"
            control={formHook.control}
            rules={formHook.validationRules.name}
            render={({field}) => (
              <TextInput
                {...field}
                id="key-name"
                type="text"
                placeholder="Friendly Key Name"
                validated={formHook.errors.name ? 'error' : 'default'}
              />
            )}
          />
          <HelperText>
            <HelperTextItem>
              A friendly name for the key for later reference. Must match ^[\s
              a-zA-Z0-9\-_:/*$.
            </HelperTextItem>
          </HelperText>
          {formHook.errors.name && (
            <HelperText>
              <HelperTextItem variant="error">
                {formHook.errors.name.message}
              </HelperTextItem>
            </HelperText>
          )}
        </FormGroup>

        <FormGroup label="Service Name:" fieldId="service-name" isRequired>
          <Controller
            name="service"
            control={formHook.control}
            rules={formHook.validationRules.service}
            render={({field}) => (
              <TextInput
                {...field}
                id="service-name"
                type="text"
                placeholder="Service Name"
                validated={formHook.errors.service ? 'error' : 'default'}
              />
            )}
          />
          <HelperText>
            <HelperTextItem>
              The name of the service for the key. Keys within the same cluster
              should share service names, representing a single logical service.
              Must match [a-z0-9_]+.
            </HelperTextItem>
          </HelperText>
          {formHook.errors.service && (
            <HelperText>
              <HelperTextItem variant="error">
                {formHook.errors.service.message}
              </HelperTextItem>
            </HelperText>
          )}
        </FormGroup>

        <FormGroup label="Expires:" fieldId="expiration" isRequired>
          <Controller
            name="expiration"
            control={formHook.control}
            rules={formHook.validationRules.expiration}
            render={({field}) => (
              <TextInput
                {...field}
                id="expiration"
                type="datetime-local"
                placeholder="YYYY-MM-DDTHH:MM"
                validated={formHook.errors.expiration ? 'error' : 'default'}
              />
            )}
          />
          <HelperText>
            <HelperTextItem>
              The date and time that the key expires. It is highly recommended
              to have an expiration date.
            </HelperTextItem>
          </HelperText>
          {formHook.errors.expiration && (
            <HelperText>
              <HelperTextItem variant="error">
                {formHook.errors.expiration.message}
              </HelperTextItem>
            </HelperText>
          )}
        </FormGroup>

        <FormGroup label="Approval Notes:" fieldId="approval-notes">
          <Controller
            name="notes"
            control={formHook.control}
            render={({field}) => (
              <TextArea
                {...field}
                id="approval-notes"
                placeholder="Enter approval notes"
                rows={4}
              />
            )}
          />
          <HelperText>
            <HelperTextItem>
              Optional notes for additional human-readable information about why
              the key was added.
            </HelperTextItem>
          </HelperText>
        </FormGroup>
      </Form>
    </Modal>
  );
};
