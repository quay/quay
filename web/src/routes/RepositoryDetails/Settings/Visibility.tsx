import {
  Alert,
  AlertActionCloseButton,
  Button,
  Spinner,
} from '@patternfly/react-core';
import Conditional from 'src/components/empty/Conditional';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {useRepositoryVisibility} from 'src/hooks/UseRepositoryVisibility';
import {useUpgradePlan} from 'src/hooks/UseUpgradePlan';
import {RepositoryDetails} from 'src/resources/RepositoryResource';

export default function Visibility(props: VisibilityProps) {
  const config = useQuayConfig();
  const {
    setVisibility,
    loading: loadingSetVisibility,
    error,
  } = useRepositoryVisibility(props.org, props.repo);
  const {
    upgrade,
    planRequired,
    maxPrivateCountReached,
    loading,
    errorFetchingPlanData,
    errorUpdatingSubscription,
    reset,
  } = useUpgradePlan(props.org, props.repoDetails?.is_organization);

  if (loading || loadingSetVisibility) {
    return <Spinner size="md" />;
  }

  if (!props.repoDetails?.is_public) {
    return (
      <>
        <div style={{paddingBottom: '1em'}}>
          This Repository is currently private. Only users on the permissions
          list may view and interact with it.
        </div>
        <Button onClick={() => setVisibility('public')}>Make Public</Button>
      </>
    );
  } else {
    const publicRepoDescription = (
      <div style={{paddingBottom: '1em'}}>
        This Repository is currently public and is visible to all users, and may
        be pulled by all users.
      </div>
    );

    if (config?.features?.BILLING && errorFetchingPlanData) {
      return (
        <>
          {publicRepoDescription}
          <Alert
            variant="danger"
            title="Unable to retrieve subscription information."
          />
        </>
      );
    }

    if (config?.features?.BILLING && planRequired != null) {
      return (
        <>
          <Conditional if={errorUpdatingSubscription != null}>
            <Alert
              variant="danger"
              title="Unable to update subscription"
              actionClose={<AlertActionCloseButton onClose={reset} />}
              style={{marginBottom: '1em'}}
            />
          </Conditional>
          {publicRepoDescription}
          <Alert
            title={
              <>
                In order to make this repository private under{' '}
                <span style={{fontWeight: 'bold'}}>{props.org}</span>, you will
                need to upgrade the namespace&apos;s plan to at least a{' '}
                <span style={{fontWeight: 'bold'}}>{planRequired?.title}</span>{' '}
                plan
              </>
            }
            variant="warning"
            style={{marginBottom: '1em'}}
          />
          <Button onClick={upgrade}>Upgrade {props.org}</Button>
        </>
      );
    }

    if (planRequired == null && !maxPrivateCountReached) {
      return (
        <>
          {publicRepoDescription}
          <Button onClick={() => setVisibility('private')}>Make Private</Button>
        </>
      );
    }

    if (config?.features?.BILLING && maxPrivateCountReached) {
      return (
        <>
          {publicRepoDescription}
          <Alert
            title="This organization has reached its private repository limit. Please contact your administrator."
            variant="warning"
            style={{marginBottom: '1em'}}
          />
        </>
      );
    }
  }
}

interface VisibilityProps {
  org: string;
  repo: string;
  repoDetails: RepositoryDetails;
}
