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
import {useOrgMirrorExists} from 'src/hooks/UseOrgMirrorExists';
import {useFetchProxyCacheConfig} from 'src/hooks/UseProxyCache';
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
    isOrgMirrored: hasConfig,
    isLoading,
    isSuccess: isOrgMirrorSuccess,
    isError: isOrgMirrorError,
  } = useOrgMirrorExists(organizationName);

  const {
    isProxyCacheConfigured,
    isLoadingProxyCacheConfig: isProxyCacheLoading,
    isErrorProxyCacheConfig: isProxyCacheError,
  } = useFetchProxyCacheConfig(organizationName);

  const {nsPolicies: immutabilityPolicies, isLoading: isPoliciesLoading} =
    useNamespaceImmutabilityPolicies(organizationName);

  const hasImmutabilityPolicies =
    !isPoliciesLoading &&
    immutabilityPolicies &&
    immutabilityPolicies.length > 0;

  // Sync selectedState when query result arrives
  useEffect(() => {
    if (isOrgMirrorSuccess) {
      setSelectedState(hasConfig ? 'MIRROR' : 'NORMAL');
    }
  }, [isOrgMirrorSuccess, hasConfig]);

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
      {isOrgMirrorError && (
        <Alert
          isInline
          variant="danger"
          title="Unable to determine current organization mirror status."
          className="pf-v5-u-mb-md"
          data-testid="org-mirror-error-alert"
        />
      )}
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
        {selectedState === 'MIRROR' && isProxyCacheError && (
          <Alert
            isInline
            variant="danger"
            title="Unable to determine proxy cache status. Organization mirroring is disabled until the proxy cache status can be verified."
            className="pf-v5-u-mb-md"
            data-testid="proxy-cache-error-alert"
          />
        )}
        {selectedState === 'MIRROR' &&
          !isProxyCacheLoading &&
          isProxyCacheConfigured && (
            <Alert
              isInline
              variant="warning"
              title="Organization mirroring cannot be enabled while a proxy cache is configured. Remove the proxy cache configuration first."
              className="pf-v5-u-mb-md"
              data-testid="proxy-cache-conflict-alert"
            />
          )}
        {selectedState === 'MIRROR' &&
          !isPoliciesLoading &&
          !hasImmutabilityPolicies &&
          !isProxyCacheLoading &&
          !isProxyCacheError &&
          !isProxyCacheConfigured && (
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
            isProxyCacheLoading ||
            isProxyCacheError ||
            (selectedState === 'MIRROR' && hasImmutabilityPolicies) ||
            (selectedState === 'MIRROR' && isProxyCacheConfigured)
          }
        >
          Submit
        </Button>
      </FormGroup>
    </Form>
  );
};
