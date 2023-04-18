import {useQuery, useQueryClient} from '@tanstack/react-query';
import {useState} from 'react';
import {
  BillingCard,
  fetchCard,
  fetchPlans,
  fetchPrivateAllowed,
  fetchSubscription,
  Plan,
  setSubscription,
  Subscription,
} from 'src/resources/BillingResource';
import {useCurrentUser} from './UseCurrentUser';
import {useQuayConfig} from './UseQuayConfig';

export function useUpgradePlan(namespace: string, isOrg: boolean) {
  const [error, setError] = useState<Error>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const queryClient = useQueryClient();
  const {user} = useCurrentUser();
  const config = useQuayConfig();
  const reset = () => {
    setError(null);
    setLoading(false);
  };

  const isOrgPlan = (plan: Plan) =>
    plan.stripeId == 'free' || plan.bus_features;

  const {
    data: plans,
    isLoading: loadingPlans,
    error: errorFetchingPlans,
  } = useQuery(['plans'], () => fetchPlans(), {
    placeholderData: [],
    enabled: config?.features?.BILLING,
  });

  const {
    data: privateAllowed,
    isLoading: loadingPrivateAllowed,
    error: errorFetchingPrivateAllowed,
  } = useQuery(
    ['privateallowed', namespace],
    () => fetchPrivateAllowed(isOrg ? namespace : null),
    {
      enabled: config?.features?.BILLING,
    },
  );

  let planRequired: Plan = null;
  let maxPrivateCountReached = false;
  if (privateAllowed?.privateAllowed || privateAllowed?.privateCount == null) {
    planRequired = null;
  } else {
    planRequired = plans
      .filter((p) => !p.deprecated)
      .filter((p) => (isOrg ? isOrgPlan(p) : true))
      .find((p) => p.privateRepos > privateAllowed?.privateCount);
    if (planRequired == undefined) {
      maxPrivateCountReached = true;
    }
  }

  const upgrade = async () => {
    let currentSubscription: Subscription = null;
    let reuseCard = true;
    try {
      currentSubscription = await fetchSubscription(isOrg ? namespace : null);
    } catch (error) {
      setError(error);
      reuseCard = false;
    }

    // If the current plan has a non-zero price, a card must already
    // must be registered
    const currentPlan: Plan = plans.find(
      (p) => p.stripeId == currentSubscription.plan,
    );
    reuseCard = reuseCard ? currentPlan.price > 0 : false;

    let cardInfo: BillingCard = null;
    try {
      cardInfo = await fetchCard(isOrg ? namespace : null);
    } catch (error) {
      setError(error);
    }

    const updateSubscription = async (
      stripeId: string,
      token: string = null,
    ) => {
      try {
        setLoading(true);
        await setSubscription(stripeId, isOrg ? namespace : null, token);
        queryClient.invalidateQueries(['privateallowed', namespace]);
        setLoading(false);
      } catch (error) {
        setError(error);
        setLoading(false);
      }
    };

    if (planRequired.price > 0 && (!cardInfo.last4 || !reuseCard)) {
      (window as any).StripeCheckout.open({
        key: config?.config?.STRIPE_PUBLISHABLE_KEY,
        email: user.email,
        amount: planRequired.price,
        currency: 'usd',
        name: 'Quay ' + planRequired.title + ' Subscription',
        description:
          'Up to ' + planRequired.privateRepos + ' private repositories',
        panelLabel: cardInfo.last4
          ? 'Subscribe'
          : `Start Trial ({{amount}} plan)`,
        token: (token) => updateSubscription(planRequired.stripeId, token.id),
        billingAddress: true,
        zipCode: true,
      });
    } else {
      updateSubscription(planRequired.stripeId);
    }
  };

  return {
    upgrade: upgrade,
    planRequired: planRequired,
    maxPrivateCountReached: maxPrivateCountReached,
    loading:
      config?.features?.BILLING &&
      (loadingPlans || loadingPrivateAllowed || loading),
    errorFetchingPlanData: errorFetchingPlans || errorFetchingPrivateAllowed,
    errorUpdatingSubscription: error,
    reset: reset,
  };
}
