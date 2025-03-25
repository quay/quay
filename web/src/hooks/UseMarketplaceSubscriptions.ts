import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {
  fetchMarketplaceSubscriptions,
  setMarketplaceOrgAttachment,
  setMarketplaceOrgRemoval,
} from 'src/resources/BillingResource';
import {useCurrentUser} from './UseCurrentUser';
import {useQuayConfig} from './UseQuayConfig';

export function useMarketplaceSubscriptions(
  organizationName: string = null,
  userName: string = null,
) {
  const config = useQuayConfig();
  const {
    isLoading: loadingUserSubs,
    isError: errorFetchingUserSubs,
    data: userSubscriptions,
  } = useQuery(
    ['subscriptions', {type: 'user'}],
    () => fetchMarketplaceSubscriptions(),
    {
      enabled: config?.features?.RH_MARKETPLACE,
    },
  );

  const {
    isLoading: loadingOrgSubs,
    error: errorFetchingOrgSubs,
    data: orgSubscriptions,
  } = useQuery(
    ['subscriptions', {type: 'org'}],
    () => fetchMarketplaceSubscriptions(organizationName),
    {
      enabled: config?.features?.RH_MARKETPLACE && organizationName != userName,
    },
  );

  const loading =
    organizationName != userName
      ? loadingUserSubs || loadingOrgSubs
      : loadingUserSubs;

  return {
    userSubscriptions: userSubscriptions,
    orgSubscriptions: orgSubscriptions,
    loading: loading,
    error: errorFetchingUserSubs,
  };
}

export function useManageOrgSubscriptions(org: string, {onSuccess, onError}) {
  const queryClient = useQueryClient();

  const {
    mutate: manageSubscription,
    isError: errorManageSubscription,
    isSuccess: successManageSubscription,
  } = useMutation(
    async ({
      subscription,
      manageType,
      bindingQuantity,
    }: {
      subscription: Dict<string>;
      manageType: string;
      bindingQuantity: number;
    }) => {
      const reqBody = [];
      const subscriptionObj = {
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
        setMarketplaceOrgAttachment(org, reqBody);
      } else {
        setMarketplaceOrgRemoval(org, reqBody);
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
  };
}
