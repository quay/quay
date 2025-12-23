import {Title} from '@patternfly/react-core';
import {AlertVariant, useUI} from 'src/contexts/UIContext';
import {useCreateOrgMirrorConfig} from 'src/hooks/UseOrgMirror';
import {OrgMirrorConfig} from 'src/resources/OrgMirrorResource';
import OrgMirrorForm from './OrgMirrorForm';
import Alerts from 'src/routes/Alerts';
import {useEffect} from 'react';

interface CreateOrgMirrorProps {
  organizationName: string;
}

export default function CreateOrgMirror({
  organizationName,
}: CreateOrgMirrorProps) {
  const {addAlert, clearAllAlerts} = useUI();

  const {createMirrorConfig, isCreating} = useCreateOrgMirrorConfig(
    organizationName,
    {
      onSuccess: () => {
        addAlert({
          variant: AlertVariant.Success,
          title: 'Organization mirror configuration created successfully',
        });
      },
      onError: (error) => {
        addAlert({
          variant: AlertVariant.Failure,
          title: error,
        });
      },
    },
  );

  useEffect(() => {
    return () => {
      clearAllAlerts();
    };
  }, []);

  const handleSubmit = async (config: OrgMirrorConfig) => {
    createMirrorConfig(config);
  };

  return (
    <>
      <Title headingLevel="h3" style={{marginBottom: '1rem'}}>
        Create Organization Mirror
      </Title>
      <p style={{marginBottom: '1.5rem'}}>
        Configure organization-level repository mirroring to automatically
        replicate repositories from an external registry into this organization.
      </p>
      <OrgMirrorForm
        organizationName={organizationName}
        onSubmit={handleSubmit}
        isSubmitting={isCreating}
        submitLabel="Create Mirror"
      />
      <Alerts />
    </>
  );
}
