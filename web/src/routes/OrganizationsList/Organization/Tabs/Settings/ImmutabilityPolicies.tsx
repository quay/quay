import {
  Alert,
  Button,
  EmptyState,
  EmptyStateActions,
  EmptyStateBody,
  EmptyStateFooter,
  EmptyStateHeader,
  EmptyStateIcon,
  Spinner,
  Title,
} from '@patternfly/react-core';
import {Table, Tbody, Td, Th, Thead, Tr} from '@patternfly/react-table';
import {LockIcon, PencilAltIcon, TrashIcon} from '@patternfly/react-icons';
import {useEffect, useState} from 'react';
import {AlertVariant, useUI} from 'src/contexts/UIContext';
import RequestError from 'src/components/errors/RequestError';
import {useOrgMirrorExists} from 'src/hooks/UseOrgMirrorExists';
import {useProxyCacheExists} from 'src/hooks/UseProxyCacheExists';
import {
  useCreateNamespaceImmutabilityPolicy,
  useDeleteNamespaceImmutabilityPolicy,
  useNamespaceImmutabilityPolicies,
  useUpdateNamespaceImmutabilityPolicy,
} from 'src/hooks/UseNamespaceImmutabilityPolicies';
import {isNullOrUndefined} from 'src/libs/utils';
import {ImmutabilityPolicy} from 'src/resources/ImmutabilityPolicyResource';
import ImmutabilityPolicyForm from 'src/components/ImmutabilityPolicyForm';
import {getErrorMessageFromUnknown} from 'src/resources/ErrorHandling';

function PolicyActionButtons({
  uuid,
  onEdit,
  onDelete,
}: {
  uuid: string;
  onEdit: (uuid: string) => void;
  onDelete: (uuid: string) => void;
}) {
  return (
    <div className="pf-v5-u-display-flex pf-v5-u-flex-direction-row">
      <Button
        variant="plain"
        onClick={() => onEdit(uuid)}
        aria-label="Edit policy"
        data-testid="edit-immutability-policy-btn"
      >
        <PencilAltIcon />
      </Button>
      <Button
        variant="plain"
        onClick={() => onDelete(uuid)}
        aria-label="Delete policy"
        data-testid="delete-immutability-policy-btn"
      >
        <TrashIcon />
      </Button>
    </div>
  );
}

export default function ImmutabilityPolicies(props: ImmutabilityPoliciesProps) {
  const [policies, setPolicies] = useState<ImmutabilityPolicy[]>([]);
  const [editingPolicyUuid, setEditingPolicyUuid] = useState<string | null>(
    null,
  );
  const [isAddingNew, setIsAddingNew] = useState(false);
  const {addAlert} = useUI();

  const {
    isOrgMirrored,
    isLoading: isOrgMirrorLoading,
    isError: isOrgMirrorError,
  } = useOrgMirrorExists(props.org);
  const {
    isProxyCacheConfigured,
    isLoading: isProxyCacheLoading,
    isError: isProxyCacheError,
  } = useProxyCacheExists(props.org);

  const {
    error,
    isSuccess: successFetchingPolicies,
    isLoading,
    nsPolicies,
    dataUpdatedAt,
  } = useNamespaceImmutabilityPolicies(props.org);

  const {createPolicy} = useCreateNamespaceImmutabilityPolicy(props.org, {
    onSuccess: () => {
      addAlert({
        title: 'Successfully created immutability policy',
        variant: AlertVariant.Success,
      });
      setIsAddingNew(false);
    },
    onError: (error) => {
      addAlert({
        title: 'Could not create immutability policy',
        variant: AlertVariant.Failure,
        message: getErrorMessageFromUnknown(error),
      });
    },
  });

  const {updatePolicy} = useUpdateNamespaceImmutabilityPolicy(props.org, {
    onSuccess: () => {
      addAlert({
        title: 'Successfully updated immutability policy',
        variant: AlertVariant.Success,
      });
      setEditingPolicyUuid(null);
    },
    onError: (error) => {
      addAlert({
        title: 'Could not update immutability policy',
        variant: AlertVariant.Failure,
        message: getErrorMessageFromUnknown(error),
      });
    },
  });

  const {deletePolicy} = useDeleteNamespaceImmutabilityPolicy(props.org, {
    onSuccess: () => {
      addAlert({
        title: 'Successfully deleted immutability policy',
        variant: AlertVariant.Success,
      });
    },
    onError: (error) => {
      addAlert({
        title: 'Could not delete immutability policy',
        variant: AlertVariant.Failure,
        message: getErrorMessageFromUnknown(error),
      });
    },
  });

  useEffect(() => {
    if (successFetchingPolicies) {
      setPolicies(nsPolicies ?? []);
    }
  }, [successFetchingPolicies, dataUpdatedAt]);

  const onSave = (
    uuid: string | null,
    tagPattern: string,
    tagPatternMatches: boolean,
  ) => {
    const policyData = {tagPattern, tagPatternMatches};
    if (isNullOrUndefined(uuid)) {
      createPolicy(policyData);
    } else {
      updatePolicy({uuid, ...policyData});
    }
  };

  const onDelete = (uuid: string) => {
    deletePolicy(uuid);
  };

  const handleAddNew = () => {
    setIsAddingNew(true);
    setEditingPolicyUuid(null);
  };

  const handleCancelAdd = () => {
    setIsAddingNew(false);
  };

  if (isLoading) {
    return <Spinner />;
  }

  if (!isNullOrUndefined(error)) {
    return <RequestError err={error} />;
  }

  const hasPolicies = policies.length > 0;

  return (
    <>
      <div className="pf-v5-u-display-flex pf-v5-u-justify-content-space-between pf-v5-u-align-items-center pf-v5-u-pb-sm">
        <Title headingLevel="h2">Immutability Policies</Title>
        {(hasPolicies || isAddingNew) && (
          <Button
            variant="primary"
            onClick={handleAddNew}
            data-testid="add-immutability-policy-btn"
            isDisabled={
              isAddingNew ||
              isOrgMirrorLoading ||
              isOrgMirrorError ||
              isOrgMirrored ||
              isProxyCacheLoading ||
              isProxyCacheError ||
              isProxyCacheConfigured
            }
          >
            Add Policy
          </Button>
        )}
      </div>
      <p className="pf-v5-u-pb-md">
        Immutability policies automatically make tags immutable based on pattern
        matching. Tags that match the configured patterns cannot be modified or
        deleted.
      </p>
      {isOrgMirrorError && (
        <Alert
          isInline
          variant="danger"
          title="Unable to determine organization mirror status. Adding immutability policies is disabled until the mirror status can be verified."
          className="pf-v5-u-mb-md"
          data-testid="org-mirror-error-alert"
        />
      )}
      {isOrgMirrored && (
        <Alert
          isInline
          variant="warning"
          title="Immutability policies cannot be added while organization-level mirroring is active. Remove the organization mirror configuration first."
          className="pf-v5-u-mb-md"
          data-testid="org-mirror-conflict-alert"
        />
      )}
      {isProxyCacheError && (
        <Alert
          isInline
          variant="danger"
          title="Unable to determine proxy cache status. Adding immutability policies is disabled until the proxy cache status can be verified."
          className="pf-v5-u-mb-md"
          data-testid="proxy-cache-error-alert"
        />
      )}
      {isProxyCacheConfigured && (
        <Alert
          isInline
          variant="warning"
          title="Immutability policies cannot be added while a proxy cache is configured. Remove the proxy cache configuration first."
          className="pf-v5-u-mb-md"
          data-testid="proxy-cache-conflict-alert"
        />
      )}

      {!hasPolicies && !isAddingNew && (
        <EmptyState>
          <EmptyStateHeader
            titleText="No immutability policies"
            headingLevel="h4"
            icon={<EmptyStateIcon icon={LockIcon} />}
          />
          <EmptyStateBody>
            Add a policy to automatically protect tags matching a pattern from
            modification or deletion.
          </EmptyStateBody>
          <EmptyStateFooter>
            <EmptyStateActions>
              <Button
                variant="primary"
                onClick={handleAddNew}
                data-testid="add-immutability-policy-btn"
                isDisabled={
                  isOrgMirrorLoading ||
                  isOrgMirrorError ||
                  isOrgMirrored ||
                  isProxyCacheLoading ||
                  isProxyCacheError ||
                  isProxyCacheConfigured
                }
              >
                Add Policy
              </Button>
            </EmptyStateActions>
          </EmptyStateFooter>
        </EmptyState>
      )}

      {!hasPolicies && isAddingNew && (
        <ImmutabilityPolicyForm
          onSave={onSave}
          onCancel={handleCancelAdd}
          policy={{tagPattern: '', tagPatternMatches: true}}
          index={0}
          successFetchingPolicies={true}
        />
      )}

      {hasPolicies && (
        <Table aria-label="Immutability policies table" variant="compact">
          <Thead>
            <Tr>
              <Th width={35}>Tag Pattern</Th>
              <Th width={45}>Behavior</Th>
              <Th width={20}>Actions</Th>
            </Tr>
          </Thead>
          <Tbody>
            {policies.map((policy, index) => {
              const isEditing = policy.uuid === editingPolicyUuid;

              if (isEditing) {
                return (
                  <Tr key={policy.uuid ?? `edit-${index}`}>
                    <Td colSpan={3}>
                      <ImmutabilityPolicyForm
                        onSave={onSave}
                        onDelete={onDelete}
                        onCancel={() => setEditingPolicyUuid(null)}
                        policy={policy}
                        index={index}
                        successFetchingPolicies={successFetchingPolicies}
                        isInline
                      />
                    </Td>
                  </Tr>
                );
              }

              return (
                <Tr key={policy.uuid ?? `policy-${index}`}>
                  <Td dataLabel="Tag Pattern">
                    <code data-testid="immutability-tag-pattern-display">
                      {policy.tagPattern}
                    </code>
                  </Td>
                  <Td dataLabel="Behavior">
                    {policy.tagPatternMatches
                      ? 'Tags matching pattern are immutable'
                      : 'Tags NOT matching pattern are immutable'}
                  </Td>
                  <Td dataLabel="Actions">
                    {policy.uuid && (
                      <PolicyActionButtons
                        uuid={policy.uuid}
                        onEdit={setEditingPolicyUuid}
                        onDelete={onDelete}
                      />
                    )}
                  </Td>
                </Tr>
              );
            })}
            {isAddingNew && (
              <Tr>
                <Td colSpan={3}>
                  <ImmutabilityPolicyForm
                    onSave={onSave}
                    onCancel={handleCancelAdd}
                    policy={{tagPattern: '', tagPatternMatches: true}}
                    index={policies.length}
                    successFetchingPolicies={true}
                    isInline
                  />
                </Td>
              </Tr>
            )}
          </Tbody>
        </Table>
      )}
    </>
  );
}

interface ImmutabilityPoliciesProps {
  org: string;
}
