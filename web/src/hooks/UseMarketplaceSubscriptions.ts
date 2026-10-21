import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {
  fetchMarketplaceSubscriptions,
  setMarketplaceOrgAttachment,
  setMarketplaceOrgRemoval,
} from 'src/resources/BillingResource';
import {useQuayConfig} from './UseQuayConfig';
import type {MarketplaceSubscription} from 'src/resources/BillingResource';

const EMPTY_SUBSCRIPTIONS: MarketplaceSubscription[] = [];

type MarketplaceSubscriptionsResult = {
  userSubscriptions: MarketplaceSubscription[];
  orgSubscriptions: MarketplaceSubscription[];
  enabled: boolean;
  loading: boolean;
  error: boolean;
};

export function useMarketplaceSubscriptions(
  organizationName: string = null,
  userName: string = null,
): MarketplaceSubscriptionsResult {
  const config = useQuayConfig();
  const enabled = !!config?.features?.RH_MARKETPLACE;
  const isOrg = !!organizationName && organizationName !== userName;
  const {
    isInitialLoading: loadingUserSubs,
    isError: errorFetchingUserSubs,
    data: userSubscriptions,
  } = useQuery(
    ['subscriptions', {type: 'user'}],
    () => fetchMarketplaceSubscriptions(),
    {
      enabled: enabled && !!userName,
    },
  );

  const {
    isInitialLoading: loadingOrgSubs,
    isError: errorFetchingOrgSubs,
    data: orgSubscriptions,
  } = useQuery(
    ['subscriptions', {type: 'org', organizationName}],
    () => fetchMarketplaceSubscriptions(organizationName),
    {
      enabled: enabled && !!userName && isOrg,
    },
  );

  const loading = isOrg ? loadingUserSubs || loadingOrgSubs : loadingUserSubs;

  return {
    userSubscriptions: Array.isArray(userSubscriptions)
      ? userSubscriptions
      : EMPTY_SUBSCRIPTIONS,
    orgSubscriptions: Array.isArray(orgSubscriptions)
      ? orgSubscriptions
      : EMPTY_SUBSCRIPTIONS,
    enabled,
    loading: loading,
    error: errorFetchingUserSubs || (isOrg && errorFetchingOrgSubs),
  };
}

export function useManageOrgSubscriptions(
  org: string,
  {
    onSuccess,
    onError,
  }: {onSuccess: () => void; onError?: (error: unknown) => void},
) {
  const queryClient = useQueryClient();

  const {
    mutate: manageSubscription,
    isError: errorManageSubscription,
    isSuccess: successManageSubscription,
    isLoading: loading,
  } = useMutation(
    async ({
      subscription,
      manageType,
      bindingQuantity,
    }: {
      subscription: MarketplaceSubscription;
      manageType: string;
      bindingQuantity: number;
    }) => {
      const reqBody: {subscription_id: string; quantity?: number}[] = [];
      const subscriptionObj: {subscription_id: string; quantity?: number} = {
        subscription_id:
          manageType === 'attach'
            ? subscription['id']
            : subscription['subscription_id'],
      };
      if (bindingQuantity) {
        subscriptionObj['quantity'] = bindingQuantity;
      }
      reqBody.push(subscriptionObj);
      if (manageType === 'attach') {
        await setMarketplaceOrgAttachment(org, reqBody);
      } else {
        await setMarketplaceOrgRemoval(org, reqBody);
      }
    },
    {
      onSuccess: () => {
        onSuccess();
        return queryClient.invalidateQueries(['subscriptions']);
      },
      onError: onError,
    },
  );
  return {
    manageSubscription,
    errorManageSubscription,
    successManageSubscription,
    loading,
  };
}
