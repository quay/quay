import {useMutation} from '@tanstack/react-query';
import {getCardSetupReturnUrls} from 'src/libs/billing';
import {createCardSetupSession} from 'src/resources/BillingResource';

export function useStripeCardSetup(namespace: string, isOrg: boolean) {
  return useMutation({
    mutationFn: () =>
      createCardSetupSession(
        getCardSetupReturnUrls(
          namespace,
          window.location.origin,
          window.location.pathname,
        ),
        isOrg ? namespace : null,
      ),
    onSuccess: (session) => window.location.assign(session.url),
  });
}
