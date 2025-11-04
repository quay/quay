import {useState} from 'react';
import {
  Modal,
  ModalVariant,
  Button,
  Form,
  FormGroup,
  TextInput,
  Alert,
} from '@patternfly/react-core';
import {useRenameOrganization} from 'src/hooks/UseOrganizationActions';
import {AlertVariant, useUI} from 'src/contexts/UIContext';
import {useFreshLogin} from 'src/hooks/UseFreshLogin';
import {FreshLoginModal} from 'src/components/modals/FreshLoginModal';

interface RenameOrganizationModalProps {
  isOpen: boolean;
  onClose: () => void;
  organizationName: string;
}

export default function RenameOrganizationModal(
  props: RenameOrganizationModalProps,
) {
  const [newName, setNewName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const {addAlert} = useUI();

  const {
    isModalOpen: isFreshLoginModalOpen,
    isLoading: isFreshLoginLoading,
    error: freshLoginError,
    showFreshLoginModal,
    handleVerify,
    handleCancel: handleFreshLoginCancel,
    isFreshLoginRequired,
  } = useFreshLogin();

  const {renameOrganization, isLoading} = useRenameOrganization({
    onSuccess: (oldName: string, newName: string) => {
      addAlert({
        variant: AlertVariant.Success,
        title: `Successfully renamed organization from ${oldName} to ${newName}`,
      });
      handleClose();
    },
    onError: (err) => {
      // Check if fresh login is required
      if (isFreshLoginRequired(err)) {
        // Show fresh login modal and retry on success
        showFreshLoginModal(() =>
          renameOrganization(props.organizationName, newName.trim()),
        );
        return;
      }

      const errorMessage =
        err?.response?.data?.error_message || 'Failed to rename organization';
      setError(errorMessage);
      addAlert({
        variant: AlertVariant.Failure,
        title: `Failed to rename organization ${props.organizationName}`,
        message: errorMessage,
      });
    },
  });

  const handleClose = () => {
    setNewName('');
    setError(null);
    props.onClose();
  };

  const handleSubmit = () => {
    if (!newName.trim()) {
      setError('Organization name cannot be empty');
      return;
    }
    setError(null);
    renameOrganization(props.organizationName, newName.trim());
  };

  return (
    <>
      <Modal
        title="Rename Organization"
        isOpen={props.isOpen}
        onClose={handleClose}
        variant={ModalVariant.medium}
        actions={[
          <Button
            key="confirm"
            variant="primary"
            onClick={handleSubmit}
            isLoading={isLoading}
            isDisabled={isLoading || !newName.trim()}
          >
            OK
          </Button>,
          <Button key="cancel" variant="link" onClick={handleClose}>
            Cancel
          </Button>,
        ]}
      >
        <Form>
          <FormGroup label="Enter a new name for the organization:" isRequired>
            <TextInput
              id="new-organization-name"
              value={newName}
              onChange={(_event, value) => setNewName(value)}
              placeholder="New organization name"
              isDisabled={isLoading}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  handleSubmit();
                }
              }}
            />
          </FormGroup>
          {error && (
            <Alert variant="danger" title="Error" isInline>
              {error}
            </Alert>
          )}
        </Form>
      </Modal>
      <FreshLoginModal
        isOpen={isFreshLoginModalOpen}
        onVerify={handleVerify}
        onCancel={handleFreshLoginCancel}
        isLoading={isFreshLoginLoading}
        error={freshLoginError}
      />
    </>
  );
}
