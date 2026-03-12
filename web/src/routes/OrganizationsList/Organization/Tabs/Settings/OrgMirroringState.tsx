import {useState, useEffect} from 'react';
import {
  Radio,
  Form,
  FormGroup,
  Button,
  Spinner,
  Alert,
} from '@patternfly/react-core';
import {useSearchParams} from 'react-router-dom';
import {useQuery} from '@tanstack/react-query';
import {isAxiosError} from 'axios';
import {getOrgMirrorConfig} from 'src/resources/OrgMirrorResource';
import {useNamespaceImmutabilityPolicies} from 'src/hooks/UseNamespaceImmutabilityPolicies';

interface OrgMirroringStateProps {
  organizationName: string;
}

export const OrgMirroringState = ({
  organizationName,
}: OrgMirroringStateProps) => {
  const [selectedState, setSelectedState] = useState<'NORMAL' | 'MIRROR'>(
    'NORMAL',
  );
  const [, setSearchParams] = useSearchParams();

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

  const {nsPolicies: immutabilityPolicies, isLoading: isPoliciesLoading} =
    useNamespaceImmutabilityPolicies(organizationName);

  const hasImmutabilityPolicies =
    !isPoliciesLoading &&
    immutabilityPolicies &&
    immutabilityPolicies.length > 0;

  const error = queryError ? 'Failed to load organization mirror state' : null;

  // Sync selectedState when query result arrives
  useEffect(() => {
    if (hasConfig !== undefined) {
      setSelectedState(hasConfig ? 'MIRROR' : 'NORMAL');
    }
  }, [hasConfig]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedState === 'MIRROR') {
      setSearchParams({tab: 'Mirroring', setup: 'true'});
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
        {selectedState === 'MIRROR' && isPoliciesLoading && (
          <Spinner size="sm" className="pf-v5-u-mb-md" />
        )}
        {selectedState === 'MIRROR' &&
          !isPoliciesLoading &&
          hasImmutabilityPolicies && (
            <Alert
              isInline
              variant="warning"
              title="Organization mirroring cannot be enabled while immutability policies are configured. Remove all namespace immutability policies first."
              className="pf-v5-u-mb-md"
              data-testid="immutability-conflict-alert"
            />
          )}
        {selectedState === 'MIRROR' &&
          !isPoliciesLoading &&
          !hasImmutabilityPolicies && (
            <Alert
              isInline
              variant="info"
              title="Selecting Mirror will take you to the Mirroring tab to configure the source registry."
              className="pf-v5-u-mb-md"
            />
          )}
        <Button
          type="submit"
          variant="primary"
          size="sm"
          isDisabled={
            selectedState === 'NORMAL' ||
            isPoliciesLoading ||
            (selectedState === 'MIRROR' && hasImmutabilityPolicies)
          }
        >
          Submit
        </Button>
      </FormGroup>
    </Form>
  );
};
