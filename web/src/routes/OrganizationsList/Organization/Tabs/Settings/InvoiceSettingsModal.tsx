import {useState} from 'react';
import {useMutation, useQueryClient} from '@tanstack/react-query';
import {isAxiosError} from 'axios';
import {
  Alert,
  Button,
  Checkbox,
  Form,
  FormGroup,
  FormHelperText,
  HelperText,
  HelperTextItem,
  Modal,
  ModalBody,
  ModalFooter,
  ModalHeader,
  ModalVariant,
  TextInput,
} from '@patternfly/react-core';
import {updateUser} from 'src/resources/UserResource';
import {updateOrgSettings} from 'src/resources/OrganizationResource';
import {AlertVariant, useUI} from 'src/contexts/UIContext';

type Props = {
  organizationName: string;
  isUserOrganization: boolean;
  enabled: boolean;
  email: string;
  onClose: () => void;
};

export function InvoiceSettingsModal({
  organizationName,
  isUserOrganization,
  enabled,
  email,
  onClose,
}: Props) {
  const [sendReceipts, setSendReceipts] = useState(enabled);
  const [emailAddress, setEmailAddress] = useState(email);
  const queryClient = useQueryClient();
  const {addAlert} = useUI();
  const validEmail = /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i.test(
    emailAddress.trim(),
  );
  const changed = sendReceipts !== enabled || emailAddress.trim() !== email;
  const save = useMutation({
    mutationFn: async () => {
      const settings = {
        invoice_email: sendReceipts,
        invoice_email_address: emailAddress.trim(),
      };
      if (isUserOrganization) await updateUser(settings);
      else await updateOrgSettings(organizationName, settings);
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries(['user']),
        queryClient.invalidateQueries(['organization', organizationName]),
      ]);
      addAlert({
        title: 'Invoice settings saved',
        variant: AlertVariant.Success,
        key: 'invoice-settings',
      });
      onClose();
    },
  });
  const close = () => {
    if (!save.isLoading) onClose();
  };
  const errorMessage = isAxiosError<{error_message?: string}>(save.error)
    ? save.error.response?.data?.error_message
    : null;

  return (
    <Modal
      isOpen
      variant={ModalVariant.small}
      onClose={close}
      aria-labelledby="invoice-settings-title"
    >
      <ModalHeader title="Invoice settings" labelId="invoice-settings-title" />
      <ModalBody>
        <Form
          id="invoice-settings-form"
          onSubmit={(event) => {
            event.preventDefault();
            if (changed && (!sendReceipts || validEmail) && !save.isLoading)
              save.mutate();
          }}
        >
          {save.isError && (
            <Alert
              isInline
              variant="danger"
              title="Unable to save invoice settings"
              isLiveRegion
            >
              {errorMessage ??
                'Please try again. Your changes have not been saved.'}
            </Alert>
          )}
          <Checkbox
            id="billing-receipts-checkbox"
            data-testid="billing-receipts-checkbox"
            label="Send receipts with email"
            isChecked={sendReceipts}
            isDisabled={save.isLoading}
            onChange={(_, checked) => setSendReceipts(checked)}
          />
          <FormGroup
            label="Receipt email address"
            fieldId="billing-invoice-email"
            isRequired={sendReceipts}
          >
            <TextInput
              id="billing-invoice-email"
              aria-describedby="billing-invoice-email-help"
              data-testid="billing-invoice-email"
              type="email"
              value={emailAddress}
              isDisabled={!sendReceipts || save.isLoading}
              isRequired={sendReceipts}
              validated={sendReceipts && !validEmail ? 'error' : 'default'}
              onChange={(_, value) => setEmailAddress(value)}
            />
            <FormHelperText>
              <HelperText id="billing-invoice-email-help" isLiveRegion>
                <HelperTextItem
                  variant={sendReceipts && !validEmail ? 'error' : 'default'}
                >
                  {sendReceipts && !validEmail
                    ? 'Enter a valid email address.'
                    : 'Receipts will be sent to this email address.'}
                </HelperTextItem>
              </HelperText>
            </FormHelperText>
          </FormGroup>
        </Form>
      </ModalBody>
      <ModalFooter>
        <Button
          variant="primary"
          type="submit"
          form="invoice-settings-form"
          data-testid="billing-save-button"
          isLoading={save.isLoading}
          isDisabled={
            !changed || (sendReceipts && !validEmail) || save.isLoading
          }
        >
          Save
        </Button>
        <Button variant="link" onClick={close} isDisabled={save.isLoading}>
          Cancel
        </Button>
      </ModalFooter>
    </Modal>
  );
}
