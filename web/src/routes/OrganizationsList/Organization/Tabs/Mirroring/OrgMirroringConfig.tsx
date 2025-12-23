import {Alert, Bullseye, Spinner} from '@patternfly/react-core';
import {useFetchOrgMirrorConfig} from 'src/hooks/UseOrgMirror';
import CreateOrgMirror from './CreateOrgMirror';
import EditOrgMirror from './EditOrgMirror';

interface OrgMirroringConfigProps {
  organizationName: string;
}

export default function OrgMirroringConfig({
  organizationName,
}: OrgMirroringConfigProps) {
  const {mirrorConfig, isLoading, isError, error} =
    useFetchOrgMirrorConfig(organizationName);

  if (isLoading) {
    return (
      <Bullseye>
        <Spinner size="lg" />
      </Bullseye>
    );
  }

  if (isError && error) {
    return (
      <Alert
        variant="danger"
        title="Error loading mirror configuration"
        isInline
      >
        {(error as Error).message || 'An unexpected error occurred'}
      </Alert>
    );
  }

  // No mirror configured - show create form
  if (!mirrorConfig) {
    return <CreateOrgMirror organizationName={organizationName} />;
  }

  // Mirror exists - show edit form with sync status
  return (
    <EditOrgMirror
      organizationName={organizationName}
      mirrorConfig={mirrorConfig}
    />
  );
}
