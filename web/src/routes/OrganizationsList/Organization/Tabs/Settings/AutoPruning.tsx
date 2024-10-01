import {Button, Spinner, Title} from '@patternfly/react-core';
import {useEffect, useState} from 'react';
import {AlertVariant} from 'src/atoms/AlertState';
import Conditional from 'src/components/empty/Conditional';
import RequestError from 'src/components/errors/RequestError';
import {useAlerts} from 'src/hooks/UseAlerts';
import {
  useCreateNamespaceAutoPrunePolicy,
  useDeleteNamespaceAutoPrunePolicy,
  useNamespaceAutoPrunePolicies,
  useUpdateNamespaceAutoPrunePolicy,
} from 'src/hooks/UseNamespaceAutoPrunePolicies';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {isNullOrUndefined} from 'src/libs/utils';
import {
  AutoPruneMethod,
  NamespaceAutoPrunePolicy,
} from 'src/resources/NamespaceAutoPruneResource';
import ReadonlyAutoprunePolicy from 'src/routes/RepositoryDetails/Settings/RepositoryAutoPruningReadonlyPolicy';
import AutoPrunePolicyForm from 'src/components/AutoPrunePolicyForm';

// Must match convert_to_timedelta from backend
export const shorthandTimeUnits = {
  s: 'seconds',
  m: 'minutes',
  h: 'hours',
  d: 'days',
  w: 'weeks',
};

export default function AutoPruning(props: AutoPruning) {
  const [policies, setPolicies] = useState([]);
  const {addAlert} = useAlerts();
  const config = useQuayConfig();
  const {
    error,
    isSuccess: successFetchingPolicies,
    isLoading,
    nsPolicies,
    dataUpdatedAt,
  } = useNamespaceAutoPrunePolicies(props.org, props.isUser);
  const {
    createPolicy,
    successCreatePolicy,
    errorCreatePolicy,
    errorCreatePolicyDetails,
  } = useCreateNamespaceAutoPrunePolicy(props.org, props.isUser);
  const {
    updatePolicy,
    successUpdatePolicy,
    errorUpdatePolicy,
    errorUpdatePolicyDetails,
  } = useUpdateNamespaceAutoPrunePolicy(props.org, props.isUser);
  const {
    deletePolicy,
    successDeletePolicy,
    errorDeletePolicy,
    errorDeletePolicyDetails,
  } = useDeleteNamespaceAutoPrunePolicy(props.org, props.isUser);

  useEffect(() => {
    if (successFetchingPolicies) {
      if (nsPolicies.length == 0) {
        addNewPolicy(true);
        return;
      }
      setPolicies(nsPolicies);
    }
  }, [successFetchingPolicies, dataUpdatedAt]);

  useEffect(() => {
    if (successCreatePolicy) {
      addAlert({
        title: 'Successfully created auto-prune policy',
        variant: AlertVariant.Success,
      });
    }
  }, [successCreatePolicy]);

  useEffect(() => {
    if (successUpdatePolicy) {
      addAlert({
        title: 'Successfully updated auto-prune policy',
        variant: AlertVariant.Success,
      });
    }
  }, [successUpdatePolicy]);

  useEffect(() => {
    if (successDeletePolicy) {
      addAlert({
        title: 'Successfully deleted auto-prune policy',
        variant: AlertVariant.Success,
      });
    }
  }, [successDeletePolicy]);

  useEffect(() => {
    if (errorCreatePolicy) {
      addAlert({
        title: 'Could not create auto-prune policy',
        variant: AlertVariant.Failure,
        message: errorCreatePolicyDetails.toString(),
      });
    }
  }, [errorCreatePolicy]);

  useEffect(() => {
    if (errorUpdatePolicy) {
      addAlert({
        title: 'Could not update auto-prune policy',
        variant: AlertVariant.Failure,
        message: errorUpdatePolicyDetails.toString(),
      });
    }
  }, [errorUpdatePolicy]);

  useEffect(() => {
    if (errorDeletePolicy) {
      addAlert({
        title: 'Could not delete auto-prune policy',
        variant: AlertVariant.Failure,
        message: errorDeletePolicyDetails.toString(),
      });
    }
  }, [errorDeletePolicy]);

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

  const onSave = (method, value, uuid, tagPattern, tagPatternMatches) => {
    if (method == AutoPruneMethod.NONE && !isNullOrUndefined(uuid)) {
      deletePolicy(uuid);
      return;
    }

    if (isNullOrUndefined(uuid)) {
      const policy: NamespaceAutoPrunePolicy = {method: method, value: value};
      if (tagPattern != '') {
        policy.tagPattern = tagPattern;
        policy.tagPatternMatches = tagPatternMatches;
      }
      createPolicy(policy);
    } else {
      const policy: NamespaceAutoPrunePolicy = {
        uuid: uuid,
        method: method,
        value: value,
      };
      if (tagPattern != '') {
        policy.tagPattern = tagPattern;
        policy.tagPatternMatches = tagPatternMatches;
      }
      updatePolicy(policy);
    }
  };

  if (isLoading) {
    return <Spinner />;
  }

  if (!isNullOrUndefined(error)) {
    return <RequestError message={error.toString()} />;
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
      <Title headingLevel="h2" style={{paddingBottom: '.5em'}}>
        Auto-Pruning Policies
      </Title>
      <p style={{paddingBottom: '1em'}}>
        Auto-pruning policies automatically delete tags across all repositories
        within this organization by a given method.
      </p>
      {policies.map((policy, index) => (
        <AutoPrunePolicyForm
          onSave={onSave}
          policy={policy}
          index={index}
          key={index}
          successFetchingPolicies={successFetchingPolicies}
        />
      ))}
      <br />
      <Button variant="primary" type="submit" onClick={() => addNewPolicy()}>
        Add Policy
      </Button>
    </>
  );
}

interface AutoPruning {
  org: string;
  isUser: boolean;
}
