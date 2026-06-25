import {
  Button,
  EmptyState,
  EmptyStateActions,
  EmptyStateBody,
  EmptyStateFooter,
  Label,
  Spinner,
  Title,
} from '@patternfly/react-core';
import {Table, Tbody, Td, Th, Thead, Tr} from '@patternfly/react-table';
import {LockIcon, PencilAltIcon, TrashIcon} from '@patternfly/react-icons';
import {useEffect, useState} from 'react';
import {AlertVariant, useUI} from 'src/contexts/UIContext';
import RequestError from 'src/components/errors/RequestError';
import {useNamespaceImmutabilityPolicies} from 'src/hooks/UseNamespaceImmutabilityPolicies';
import {useOrganization} from 'src/hooks/UseOrganization';
import {
  useCreateRepositoryImmutabilityPolicy,
  useDeleteRepositoryImmutabilityPolicy,
  useFetchRepositoryImmutabilityPolicies,
  useUpdateRepositoryImmutabilityPolicy,
} from 'src/hooks/UseRepositoryImmutabilityPolicies';
import {isNullOrUndefined} from 'src/libs/utils';
import {ImmutabilityPolicy} from 'src/resources/ImmutabilityPolicyResource';
import ImmutabilityPolicyForm from 'src/components/ImmutabilityPolicyForm';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
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
    <div
      className="pf-v6-u-display-flex pf-v6-u-flex-direction-row pf-v6-u-align-items-center"
      style={{minHeight: '36px'}}
    >
      <Button
        icon={<PencilAltIcon />}
        variant="plain"
        onClick={() => onEdit(uuid)}
        aria-label="Edit policy"
        data-testid="edit-immutability-policy-btn"
      />
      <Button
        icon={<TrashIcon />}
        variant="plain"
        onClick={() => onDelete(uuid)}
        aria-label="Delete policy"
        data-testid="delete-immutability-policy-btn"
      />
    </div>
  );
}

interface PolicyWithScope extends ImmutabilityPolicy {
  scope: 'namespace' | 'repository';
}

export default function RepositoryImmutabilityPolicies(
  props: RepositoryImmutabilityPoliciesProps,
) {
  const [repoPolicies, setRepoPolicies] = useState<ImmutabilityPolicy[]>([]);
  const [editingPolicyUuid, setEditingPolicyUuid] = useState<string | null>(
    null,
  );
  const [isAddingNew, setIsAddingNew] = useState(false);
  const {addAlert} = useUI();
  const {organization} = useOrganization(props.organizationName);
  const {user} = useCurrentUser();

  const canViewNsPolicies =
    organization?.is_admin || user?.username === props.organizationName;

  const {isSuccess: successFetchingNsPolicies, nsPolicies} =
    useNamespaceImmutabilityPolicies(props.organizationName, canViewNsPolicies);

  const {
    errorFetchingRepoPolicies,
    successFetchingRepoPolicies,
    isLoadingRepoPolicies,
    repoPolicies: fetchedRepoPolicies,
    repoPoliciesDataUpdatedAt,
  } = useFetchRepositoryImmutabilityPolicies(
    props.organizationName,
    props.repoName,
  );

  const {createRepoPolicy} = useCreateRepositoryImmutabilityPolicy(
    props.organizationName,
    props.repoName,
    {
      onSuccess: () => {
        addAlert({
          title: 'Successfully created repository immutability policy',
          variant: AlertVariant.Success,
        });
        setIsAddingNew(false);
      },
      onError: (error) => {
        addAlert({
          title: 'Could not create repository immutability policy',
          variant: AlertVariant.Failure,
          message: getErrorMessageFromUnknown(error),
        });
      },
    },
  );

  const {updateRepoPolicy} = useUpdateRepositoryImmutabilityPolicy(
    props.organizationName,
    props.repoName,
    {
      onSuccess: () => {
        addAlert({
          title: 'Successfully updated repository immutability policy',
          variant: AlertVariant.Success,
        });
        setEditingPolicyUuid(null);
      },
      onError: (error) => {
        addAlert({
          title: 'Could not update repository immutability policy',
          variant: AlertVariant.Failure,
          message: getErrorMessageFromUnknown(error),
        });
      },
    },
  );

  const {deleteRepoPolicy} = useDeleteRepositoryImmutabilityPolicy(
    props.organizationName,
    props.repoName,
    {
      onSuccess: () => {
        addAlert({
          title: 'Successfully deleted repository immutability policy',
          variant: AlertVariant.Success,
        });
      },
      onError: (error) => {
        addAlert({
          title: 'Could not delete repository immutability policy',
          variant: AlertVariant.Failure,
          message: getErrorMessageFromUnknown(error),
        });
      },
    },
  );

  useEffect(() => {
    if (successFetchingRepoPolicies) {
      setRepoPolicies(fetchedRepoPolicies ?? []);
    }
  }, [
    successFetchingRepoPolicies,
    successFetchingNsPolicies,
    repoPoliciesDataUpdatedAt,
  ]);

  const onSave = (
    uuid: string | null,
    tagPattern: string,
    tagPatternMatches: boolean,
  ) => {
    const policyData = {tagPattern, tagPatternMatches};
    if (isNullOrUndefined(uuid)) {
      createRepoPolicy(policyData);
    } else {
      updateRepoPolicy({uuid, ...policyData});
    }
  };

  const onDelete = (uuid: string) => {
    deleteRepoPolicy(uuid);
  };

  const handleAddNew = () => {
    setIsAddingNew(true);
    setEditingPolicyUuid(null);
  };

  const handleCancelAdd = () => {
    setIsAddingNew(false);
  };

  if (isLoadingRepoPolicies) {
    return <Spinner />;
  }

  if (!isNullOrUndefined(errorFetchingRepoPolicies)) {
    return <RequestError err={errorFetchingRepoPolicies} />;
  }

  // Combine namespace and repository policies with scope
  const allPolicies: PolicyWithScope[] = [
    ...(canViewNsPolicies && nsPolicies
      ? nsPolicies.map((p) => ({...p, scope: 'namespace' as const}))
      : []),
    ...repoPolicies.map((p) => ({...p, scope: 'repository' as const})),
  ];

  const hasPolicies = allPolicies.length > 0;

  return (
    <>
      <div className="pf-v6-u-display-flex pf-v6-u-justify-content-space-between pf-v6-u-align-items-center pf-v6-u-pb-sm">
        <Title headingLevel="h2">Immutability Policies</Title>
        {(hasPolicies || isAddingNew) && (
          <Button
            variant="primary"
            onClick={handleAddNew}
            data-testid="add-repo-immutability-policy-btn"
            isDisabled={isAddingNew}
          >
            Add Policy
          </Button>
        )}
      </div>
      <p className="pf-v6-u-pb-md">
        Immutability policies automatically make tags immutable based on pattern
        matching. Tags that match the configured patterns cannot be modified or
        deleted.
      </p>

      {!hasPolicies && !isAddingNew && (
        <EmptyState
          headingLevel="h4"
          icon={LockIcon}
          titleText="No immutability policies"
        >
          <EmptyStateBody>
            Add a policy to automatically protect tags matching a pattern from
            modification or deletion.
          </EmptyStateBody>
          <EmptyStateFooter>
            <EmptyStateActions>
              <Button
                variant="primary"
                onClick={handleAddNew}
                data-testid="add-repo-immutability-policy-btn"
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
              <Th width={15}>Scope</Th>
              <Th width={30}>Tag Pattern</Th>
              <Th width={40}>Behavior</Th>
              <Th width={15}>Actions</Th>
            </Tr>
          </Thead>
          <Tbody>
            {allPolicies.map((policy, index) => {
              const isEditing =
                policy.scope === 'repository' &&
                policy.uuid === editingPolicyUuid;

              if (isEditing) {
                return (
                  <Tr key={policy.uuid ?? `edit-${index}`}>
                    <Td colSpan={4}>
                      <ImmutabilityPolicyForm
                        onSave={onSave}
                        onDelete={onDelete}
                        onCancel={() => setEditingPolicyUuid(null)}
                        policy={policy}
                        index={index}
                        successFetchingPolicies={successFetchingRepoPolicies}
                        isInline
                      />
                    </Td>
                  </Tr>
                );
              }

              return (
                <Tr key={policy.uuid ?? `policy-${index}`}>
                  <Td dataLabel="Scope">
                    <Label
                      color={policy.scope === 'namespace' ? 'blue' : 'green'}
                      isCompact
                    >
                      {policy.scope === 'namespace'
                        ? 'Namespace'
                        : 'Repository'}
                    </Label>
                  </Td>
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
                    {policy.scope === 'repository' && policy.uuid && (
                      <PolicyActionButtons
                        uuid={policy.uuid}
                        onEdit={setEditingPolicyUuid}
                        onDelete={onDelete}
                      />
                    )}
                    {policy.scope === 'namespace' && (
                      <div
                        className="pf-v6-u-display-flex pf-v6-u-align-items-center pf-v6-u-color-200"
                        style={{minHeight: '36px'}}
                      >
                        Inherited
                      </div>
                    )}
                  </Td>
                </Tr>
              );
            })}
            {isAddingNew && (
              <Tr>
                <Td colSpan={4}>
                  <ImmutabilityPolicyForm
                    onSave={onSave}
                    onCancel={handleCancelAdd}
                    policy={{tagPattern: '', tagPatternMatches: true}}
                    index={allPolicies.length}
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

interface RepositoryImmutabilityPoliciesProps {
  organizationName: string;
  repoName: string;
}
