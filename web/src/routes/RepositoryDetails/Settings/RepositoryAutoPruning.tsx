import {Button, Spinner, Title} from '@patternfly/react-core';
import {useEffect, useState} from 'react';
import {AlertVariant} from 'src/atoms/AlertState';
import Conditional from 'src/components/empty/Conditional';
import RequestError from 'src/components/errors/RequestError';
import {useAlerts} from 'src/hooks/UseAlerts';
import {useNamespaceAutoPrunePolicies} from 'src/hooks/UseNamespaceAutoPrunePolicies';
import {useOrganization} from 'src/hooks/UseOrganization';
import {
  useCreateRepositoryAutoPrunePolicy,
  useDeleteRepositoryAutoPrunePolicy,
  useFetchRepositoryAutoPrunePolicies,
  useUpdateRepositoryAutoPrunePolicy,
} from 'src/hooks/UseRepositoryAutoPrunePolicies';
import {isNullOrUndefined} from 'src/libs/utils';
import {AutoPruneMethod} from 'src/resources/NamespaceAutoPruneResource';
import {RepositoryAutoPrunePolicy} from 'src/resources/RepositoryAutoPruneResource';
import ReadonlyAutoprunePolicy from './RepositoryAutoPruningReadonlyPolicy';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import AutoPrunePolicyForm from 'src/components/AutoPrunePolicyForm';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';

export default function RepositoryAutoPruning(props: RepositoryAutoPruning) {
  const [policies, setPolicies] = useState([]);
  const {addAlert} = useAlerts();
  const {organization} = useOrganization(props.organizationName);
  const {user} = useCurrentUser();
  const config = useQuayConfig();

  const {isSuccess: successFetchingPolicies, nsPolicies} =
    useNamespaceAutoPrunePolicies(
      props.organizationName,
      props.isUser,
      organization?.is_admin || user?.username == props.organizationName,
    );

  const {
    errorFetchingRepoPolicies,
    successFetchingRepoPolicies,
    isLoadingRepoPolicies,
    repoPolicies,
    repoPoliciesDataUpdatedAt,
  } = useFetchRepositoryAutoPrunePolicies(
    props.organizationName,
    props.repoName,
  );

  const {
    createRepoPolicy,
    successRepoPolicyCreation,
    errorRepoPolicyCreation,
    errorDetailsRepoPolicyCreation,
  } = useCreateRepositoryAutoPrunePolicy(
    props.organizationName,
    props.repoName,
  );

  const {
    updateRepoPolicy,
    successRepoPolicyUpdation,
    errorRepoPolicyUpdation,
    errorDetailsRepoPolicyUpdation,
  } = useUpdateRepositoryAutoPrunePolicy(
    props.organizationName,
    props.repoName,
  );

  const {
    deleteRepoPolicy,
    successRepoPolicyDeletion,
    errorRepoPolicyDeletion,
    errorDetailsRepoPolicyDeletion,
  } = useDeleteRepositoryAutoPrunePolicy(
    props.organizationName,
    props.repoName,
  );

  const addNewPolicy = (clear_existing = false) => {
    if (clear_existing) {
      setPolicies([
        {
          method: AutoPruneMethod.NONE,
          uuid: null,
          value: null,
          tagPattern: null,
          tagPatternMatches: true,
        },
      ]);
    } else {
      setPolicies([
        ...policies,
        {
          method: AutoPruneMethod.NONE,
          uuid: null,
          value: null,
          tagPattern: null,
          tagPatternMatches: true,
        },
      ]);
    }
  };

  useEffect(() => {
    if (successFetchingRepoPolicies) {
      if (repoPolicies.length == 0) {
        addNewPolicy(true);
        return;
      }
      setPolicies(repoPolicies);
    }
  }, [
    successFetchingRepoPolicies,
    successFetchingPolicies,
    repoPoliciesDataUpdatedAt,
  ]);

  useEffect(() => {
    if (successRepoPolicyCreation) {
      addAlert({
        title: 'Successfully created repository auto-prune policy',
        variant: AlertVariant.Success,
      });
    }
  }, [successRepoPolicyCreation]);

  useEffect(() => {
    if (successRepoPolicyUpdation) {
      addAlert({
        title: 'Successfully updated repository auto-prune policy',
        variant: AlertVariant.Success,
      });
    }
  }, [successRepoPolicyUpdation]);

  useEffect(() => {
    if (successRepoPolicyDeletion) {
      addAlert({
        title: 'Successfully deleted repository auto-prune policy',
        variant: AlertVariant.Success,
      });
    }
  }, [successRepoPolicyDeletion]);

  useEffect(() => {
    if (errorRepoPolicyCreation) {
      addAlert({
        title: 'Could not create repository auto-prune policy',
        variant: AlertVariant.Failure,
        message: errorDetailsRepoPolicyCreation.toString(),
      });
    }
  }, [errorRepoPolicyCreation]);

  useEffect(() => {
    if (errorRepoPolicyUpdation) {
      addAlert({
        title: 'Could not update repository auto-prune policy',
        variant: AlertVariant.Failure,
        message: errorDetailsRepoPolicyUpdation.toString(),
      });
    }
  }, [errorRepoPolicyUpdation]);

  useEffect(() => {
    if (errorRepoPolicyDeletion) {
      addAlert({
        title: 'Could not delete repository auto-prune policy',
        variant: AlertVariant.Failure,
        message: errorDetailsRepoPolicyDeletion.toString(),
      });
    }
  }, [errorRepoPolicyDeletion]);

  const onSave = (method, value, uuid, tagPattern, tagPatternMatches) => {
    if (method == AutoPruneMethod.NONE && !isNullOrUndefined(uuid)) {
      deleteRepoPolicy(uuid);
      return;
    }

    if (isNullOrUndefined(uuid)) {
      const policy: RepositoryAutoPrunePolicy = {method: method, value: value};
      if (tagPattern != '') {
        policy.tagPattern = tagPattern;
        policy.tagPatternMatches = tagPatternMatches;
      }
      createRepoPolicy(policy);
    } else {
      const policy: RepositoryAutoPrunePolicy = {
        uuid: uuid,
        method: method,
        value: value,
      };
      if (tagPattern != '') {
        policy.tagPattern = tagPattern;
        policy.tagPatternMatches = tagPatternMatches;
      }
      updateRepoPolicy(policy);
    }
  };

  if (isLoadingRepoPolicies) {
    return <Spinner />;
  }

  if (!isNullOrUndefined(errorFetchingRepoPolicies)) {
    return <RequestError message={errorFetchingRepoPolicies.toString()} />;
  }

  return (
    <>
      <Conditional
        if={config?.config?.DEFAULT_NAMESPACE_AUTOPRUNE_POLICY != null}
      >
        <ReadonlyAutoprunePolicy
          testId="registry-autoprune-policy"
          title="Registry Auto-Pruning Policy"
          policies={[config?.config?.DEFAULT_NAMESPACE_AUTOPRUNE_POLICY]}
        />
      </Conditional>
      <Conditional
        if={
          nsPolicies?.length > 0 &&
          (props.isUser
            ? user?.username == props.organizationName
            : organization?.is_admin)
        }
      >
        <ReadonlyAutoprunePolicy
          testId="namespace-autoprune-policy"
          title="Namespace Auto-Pruning Policies"
          policies={nsPolicies}
        />
      </Conditional>
      <Title headingLevel="h2" style={{paddingBottom: '.5em'}}>
        Repository Auto-Pruning Policies
      </Title>
      <p style={{paddingBottom: '1em'}}>
        Auto-pruning policies automatically delete tags under this repository by
        a given method.
      </p>
      {policies.map((policy, index) => (
        <AutoPrunePolicyForm
          onSave={onSave}
          policy={policy}
          index={index}
          key={index}
          successFetchingPolicies={successFetchingRepoPolicies}
        />
      ))}
      <br />
      <Button variant="primary" type="submit" onClick={() => addNewPolicy()}>
        Add Policy
      </Button>
    </>
  );
}

interface RepositoryAutoPruning {
  organizationName: string;
  repoName: string;
  isUser: boolean;
}
