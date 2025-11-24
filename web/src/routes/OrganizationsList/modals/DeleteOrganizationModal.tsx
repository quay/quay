import {useState} from 'react';
import {Modal, ModalVariant, Button, Text, Alert} from '@patternfly/react-core';
import {useDeleteSingleOrganization} from 'src/hooks/UseOrganizationActions';
import {AlertVariant, useUI} from 'src/contexts/UIContext';
import {isFreshLoginError} from 'src/utils/freshLoginErrors';
import {OrganizationsTableItem} from '../OrganizationsList';

interface DeleteOrganizationModalProps {
  isOpen: boolean;
  onClose: () => void;
  organizationName: string;
  selectedOrganization?: OrganizationsTableItem[];
  setSelectedOrganization?: (orgs: OrganizationsTableItem[]) => void;
}

export default function DeleteOrganizationModal(
  props: DeleteOrganizationModalProps,
) {
  const [error, setError] = useState<string | null>(null);
  const {addAlert} = useUI();

  const {deleteOrganization, isLoading} = useDeleteSingleOrganization({
    onSuccess: () => {
      addAlert({
        variant: AlertVariant.Success,
        title: `Successfully deleted organization ${props.organizationName}`,
      });
      // Remove the deleted organization from selectedOrganization state
      if (props.setSelectedOrganization && props.selectedOrganization) {
        props.setSelectedOrganization(
          props.selectedOrganization.filter(
            (org) => org.name !== props.organizationName,
          ),
        );
      }
      handleClose();
    },
    onError: (err) => {
      const errorMessage =
        err?.response?.data?.error_message ||
        err?.message ||
        'Failed to delete organization';
      // Filter out fresh login errors to prevent duplicate alerts
      if (isFreshLoginError(errorMessage)) {
        return;
      }
      setError(errorMessage);
      addAlert({
        variant: AlertVariant.Failure,
        title: `Failed to delete organization ${props.organizationName}`,
        message: errorMessage,
      });
    },
  });

  const handleClose = () => {
    setError(null);
    props.onClose();
  };

  const handleDelete = () => {
    setError(null);
    deleteOrganization(props.organizationName);
    // Close modal; request is queued if fresh login required
    handleClose();
  };

  return (
    <Modal
      title="Delete Organization"
      isOpen={props.isOpen}
      onClose={handleClose}
      variant={ModalVariant.medium}
      actions={[
        <Button
          key="confirm"
          variant="danger"
          onClick={handleDelete}
          isLoading={isLoading}
          isDisabled={isLoading}
        >
          OK
        </Button>,
        <Button key="cancel" variant="link" onClick={handleClose}>
          Cancel
        </Button>,
      ]}
    >
      <Text>
        Are you sure you want to delete this organization? Its data will be
        deleted with it.
      </Text>
      {error && (
        <Alert variant="danger" title="Error" isInline style={{marginTop: 16}}>
          {error}
        </Alert>
      )}
    </Modal>
  );
}
