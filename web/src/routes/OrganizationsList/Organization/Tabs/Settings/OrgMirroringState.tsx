import {useState, useEffect} from 'react';
import {
  Radio,
  Form,
  FormGroup,
  Button,
  Spinner,
  Alert,
  Modal,
  ModalVariant,
} from '@patternfly/react-core';
import {useSearchParams} from 'react-router-dom';
import {useQuery, useQueryClient} from '@tanstack/react-query';
import {isAxiosError} from 'axios';
import {useUI, AlertVariant} from 'src/contexts/UIContext';
import {
  getOrgMirrorConfig,
  deleteOrgMirrorConfig,
} from 'src/resources/OrgMirrorResource';

interface OrgMirroringStateProps {
  organizationName: string;
}

export const OrgMirroringState = ({
  organizationName,
}: OrgMirroringStateProps) => {
  const [selectedState, setSelectedState] = useState<'NORMAL' | 'MIRROR'>(
    'NORMAL',
  );
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const {addAlert} = useUI();

  const {
    data: hasConfig,
    isLoading,
    error: queryError,
  } = useQuery<boolean>({
    queryKey: ['org-mirror-config-exists', organizationName],
    queryFn: async () => {
      try {
        await getOrgMirrorConfig(organizationName);
        return true;
      } catch (err) {
        if (isAxiosError(err) && err.response?.status === 404) {
          return false;
        }
        throw err;
      }
    },
  });

  const error = queryError ? 'Failed to load organization mirror state' : null;

  // Sync selectedState when query result arrives
  useEffect(() => {
    if (hasConfig !== undefined) {
      setSelectedState(hasConfig ? 'MIRROR' : 'NORMAL');
    }
  }, [hasConfig]);

  const handleDelete = async () => {
    if (isDeleting) return;
    setIsDeleting(true);
    try {
      await deleteOrgMirrorConfig(organizationName);
      queryClient.invalidateQueries({
        queryKey: ['org-mirror-config-exists', organizationName],
      });
      queryClient.invalidateQueries({
        queryKey: ['org-mirror-config', organizationName],
      });
      addAlert({
        variant: AlertVariant.Success,
        title: 'Organization mirror configuration deleted successfully',
      });
    } catch (err: unknown) {
      addAlert({
        variant: AlertVariant.Failure,
        title: 'Error deleting organization mirror configuration',
        message: (err as Error).message,
      });
    } finally {
      setIsDeleting(false);
      setIsDeleteModalOpen(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedState === 'MIRROR') {
      setSearchParams({tab: 'Mirroring', setup: 'true'});
    } else if (selectedState === 'NORMAL' && hasConfig) {
      setIsDeleteModalOpen(true);
    }
  };

  if (isLoading) {
    return <Spinner size="md" />;
  }

  return (
    <Form onSubmit={handleSubmit}>
      {error && <Alert variant="danger" isInline title={error} />}
      <FormGroup fieldId="organization-state">
        <Radio
          isChecked={selectedState === 'NORMAL'}
          name="orgState"
          onChange={() => setSelectedState('NORMAL')}
          label="Normal"
          id="normal"
          value="normal"
          description="The organization will be in its standard operational state."
          className="pf-v5-u-mb-md"
        />
        <Radio
          isChecked={selectedState === 'MIRROR'}
          name="orgState"
          onChange={() => setSelectedState('MIRROR')}
          label="Mirror"
          id="mirror"
          value="mirror"
          description="Mirror all repositories from a source registry namespace. When an organization is set as mirrored, repositories are automatically discovered and synced from the source."
          className="pf-v5-u-mb-md"
        />
        {selectedState === 'MIRROR' && !hasConfig && (
          <Alert
            isInline
            variant="info"
            title="Selecting Mirror will take you to the Mirroring tab to configure the source registry."
            className="pf-v5-u-mb-md"
          />
        )}
        {selectedState === 'NORMAL' && hasConfig && (
          <Alert
            isInline
            variant="warning"
            title="Switching to Normal will delete the organization mirror configuration and stop all future syncs."
            className="pf-v5-u-mb-md"
          />
        )}
        <Button
          type="submit"
          variant="primary"
          size="sm"
          isDisabled={
            (selectedState === 'NORMAL' && !hasConfig) ||
            (selectedState === 'MIRROR' && hasConfig)
          }
        >
          Submit
        </Button>
        <Modal
          variant={ModalVariant.small}
          title="Disable Organization Mirroring"
          isOpen={isDeleteModalOpen}
          onClose={() => setIsDeleteModalOpen(false)}
          actions={[
            <Button
              key="confirm"
              variant="danger"
              onClick={handleDelete}
              isDisabled={isDeleting}
              isLoading={isDeleting}
              data-testid="confirm-disable-mirror-button"
            >
              Confirm
            </Button>,
            <Button
              key="cancel"
              variant="link"
              onClick={() => setIsDeleteModalOpen(false)}
            >
              Cancel
            </Button>,
          ]}
        >
          Are you sure you want to switch back to Normal? This will delete the
          organization mirror configuration and stop all future syncs. Existing
          mirrored repositories will remain.
        </Modal>
      </FormGroup>
    </Form>
  );
};
