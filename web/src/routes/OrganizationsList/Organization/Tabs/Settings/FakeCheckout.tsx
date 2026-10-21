import {useState} from 'react';
import {useSearchParams} from 'react-router-dom';
import {useMutation, useQuery} from '@tanstack/react-query';
import {
  Alert,
  Button,
  Card,
  CardBody,
  Content,
  Skeleton,
  Stack,
  Title,
} from '@patternfly/react-core';
import {
  completeFakeCheckout,
  fetchFakeCheckout,
} from 'src/resources/BillingResource';
import {formatPlanPrice, getBillingErrorMessage} from 'src/libs/billing';

const FakeCheckout: React.FC = () => {
  const [params] = useSearchParams();
  const session = params.get('session');
  const organization = params.get('organization');
  const [leaving, setLeaving] = useState(false);
  const details = useQuery(
    ['fake-checkout', session, organization],
    () => fetchFakeCheckout(session, organization),
    {enabled: !!session, retry: false},
  );
  const complete = useMutation({
    retry: false,
    mutationFn: () => completeFakeCheckout(session, organization),
    onSuccess: ({url}) => {
      const target = new URL(url);
      if (target.origin !== window.location.origin)
        throw new Error('The checkout return URL does not match this site.');
      setLeaving(true);
      window.location.assign(target.toString());
    },
  });

  return (
    <Stack
      hasGutter
      style={{maxWidth: '720px'}}
      data-testid="fake-checkout-page"
    >
      <Title headingLevel="h1">Simulated checkout</Title>
      <Alert
        isLiveRegion
        isInline
        variant="info"
        title="Local FakeStripe checkout"
      >
        This is a development simulation. No payment is collected. Do not enter
        real payment details.
      </Alert>
      {!session || details.isError ? (
        <Alert
          isLiveRegion
          isInline
          variant="danger"
          title="Unable to load simulated checkout"
        >
          {session
            ? getBillingErrorMessage(details.error)
            : 'The checkout session is missing.'}
        </Alert>
      ) : details.isLoading ? (
        <Skeleton
          height="200px"
          screenreaderText="Loading simulated checkout"
        />
      ) : (
        details.data && (
          <Card>
            <CardBody>
              <Stack hasGutter>
                <Title headingLevel="h2">
                  {details.data.plan
                    ? `Subscribe to ${details.data.plan.title}`
                    : 'Update payment method'}
                </Title>
                {organization && (
                  <Content>Organization: {organization}</Content>
                )}
                {details.data.plan && (
                  <Content>
                    {formatPlanPrice(details.data.plan.price)} ·{' '}
                    {details.data.plan.privateRepos} private repositories
                  </Content>
                )}
                <Content>
                  Completing this simulation saves a sample Visa ending in 4242.
                </Content>
                {complete.isError && (
                  <Alert
                    isLiveRegion
                    isInline
                    variant="danger"
                    title="Simulated checkout could not be completed"
                  >
                    {getBillingErrorMessage(complete.error)}
                  </Alert>
                )}
                <div>
                  <Button
                    isLoading={complete.isLoading || leaving}
                    isDisabled={complete.isLoading || leaving}
                    onClick={() => complete.mutate()}
                  >
                    Complete simulated checkout
                  </Button>{' '}
                  <Button
                    variant="link"
                    isDisabled={complete.isLoading || leaving}
                    onClick={() => {
                      const target = new URL(details.data.cancel_url);
                      if (target.origin === window.location.origin)
                        window.location.assign(target.toString());
                    }}
                  >
                    Cancel
                  </Button>
                </div>
              </Stack>
            </CardBody>
          </Card>
        )
      )}
    </Stack>
  );
};

export default FakeCheckout;
