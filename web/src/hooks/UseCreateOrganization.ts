import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {createOrg} from 'src/resources/OrganizationResource';
import {
  createSubscriptionCheckoutSession,
  fetchPlans,
  fetchSubscription,
} from 'src/resources/BillingResource';
import {getPlanCheckoutReturnUrls} from 'src/libs/billing';

export function useCreateOrganization(billingEnabled: boolean) {
  const queryClient = useQueryClient();
  const plans = useQuery(['plans'], fetchPlans, {enabled: billingEnabled});
  const creation = useMutation({
    retry: false,
    mutationFn: async ({name, email}: {name: string; email?: string}) => {
      await createOrg(name, email);
      return {name};
    },
    onSuccess: () => {
      void queryClient.invalidateQueries(['user']);
      void queryClient.invalidateQueries(['organization', 'superuser']);
    },
  });
  const checkout = useMutation({
    retry: false,
    mutationFn: async ({name, plan}: {name: string; plan: string}) => {
      // A previous Checkout attempt may have completed before a retry.
      const subscription = await fetchSubscription(name);
      if (subscription.hasSubscription) return null;
      return createSubscriptionCheckoutSession(
        plan,
        getPlanCheckoutReturnUrls(
          name,
          window.location.origin,
          plan,
          window.location.pathname,
        ),
        name,
      );
    },
  });
  return {plans, creation, checkout};
}
