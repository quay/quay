import {useEffect, useState} from 'react';
import {
  Alert,
  ActionList,
  ActionListItem,
  Button,
  Content,
  Flex,
  Skeleton,
  Stack,
  Title,
} from '@patternfly/react-core';
import {Link, useNavigate, useSearchParams} from 'react-router-dom';
import {useQueryClient} from '@tanstack/react-query';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
import {useOrganization} from 'src/hooks/UseOrganization';
import {useRepositories} from 'src/hooks/UseRepositories';
import {useUpgradePlan} from 'src/hooks/UseUpgradePlan';
import {useCard} from 'src/hooks/UseCard';
import {useInvoices} from 'src/hooks/UseInvoices';
import {useMarketplaceSubscriptions} from 'src/hooks/UseMarketplaceSubscriptions';
import {useStripeCardSetup} from 'src/hooks/UseStripeCardSetup';
import {NavigationPath} from 'src/routes/NavigationPath';
import Alerts from 'src/routes/Alerts';
import {CurrentPlanSection} from './CurrentPlanSection';
import {UsageSection} from './UsageSection';
import {PaymentMethodSection} from './PaymentMethodSection';
import MarketplaceDetails from './MarketplaceDetails';
import {InvoiceSettingsModal} from './InvoiceSettingsModal';
import {getBillingErrorMessage, isPlanChangeConfirmed} from 'src/libs/billing';

type BillingInformationProps = {organizationName: string};
const MAX_SAFE = Number.MAX_SAFE_INTEGER;

export const BillingInformation = ({
  organizationName,
}: BillingInformationProps) => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  const {user} = useCurrentUser();
  const [invoiceSettingsOpen, setInvoiceSettingsOpen] = useState(false);
  const {organization, isUserOrganization} = useOrganization(organizationName);
  const settings = isUserOrganization ? user : organization;
  const stripeSetup = useStripeCardSetup(organizationName, !isUserOrganization);
  const checkoutResult = searchParams.get('paymentMethod');
  const planCheckoutResult = searchParams.get('planCheckout');
  const planReturned =
    planCheckoutResult === 'returned' ||
    searchParams.get('planChange') === 'returned';
  const expectedPlan = searchParams.get('checkoutPlan');
  const [checkingCheckout, setCheckingCheckout] = useState(false);

  useEffect(() => {
    if (checkoutResult !== 'returned' && !planReturned) {
      setCheckingCheckout(false);
      return;
    }
    // Stripe's webhook may finish after Checkout redirects back to Quay.
    setCheckingCheckout(true);
    const refresh = () => {
      void queryClient.invalidateQueries(['card', organizationName]);
      void queryClient.invalidateQueries([
        'organization',
        isUserOrganization ? null : organizationName,
        'plan',
      ]);
      void queryClient.invalidateQueries(['privateallowed', organizationName]);
      void queryClient.invalidateQueries(['invoices', organizationName]);
    };
    refresh();
    let refreshes = 0;
    const interval = window.setInterval(() => {
      refresh();
      refreshes += 1;
      if (refreshes >= 5) {
        window.clearInterval(interval);
        setCheckingCheckout(false);
      }
    }, 2000);
    return () => window.clearInterval(interval);
  }, [
    checkoutResult,
    planReturned,
    organizationName,
    isUserOrganization,
    queryClient,
  ]);

  const {
    currentPlan,
    currentPlanIsLoading,
    currentPlanIsFetchedAfterMount,
    currentPlanError,
    plans,
    privateCount,
  } = useUpgradePlan(organizationName, !isUserOrganization);
  const {
    card,
    isLoading: cardLoading,
    isError: cardError,
  } = useCard(organizationName, !isUserOrganization);
  const {totalResults: publicCount} = useRepositories(organizationName, false);
  const {
    invoices,
    isLoading: invoicesLoading,
    isError: invoicesError,
  } = useInvoices(organizationName, !isUserOrganization);
  const {
    userSubscriptions,
    orgSubscriptions,
    loading: portalLoading,
    error: portalError,
  } = useMarketplaceSubscriptions(organizationName, user?.username);
  const portalSubscriptions = isUserOrganization
    ? userSubscriptions.filter(
        (subscription) => subscription.assigned_to_org == null,
      )
    : orgSubscriptions;
  const portalAllowance =
    portalLoading || portalError
      ? 0
      : portalSubscriptions.reduce(
          (total, subscription) =>
            total +
            subscription.quantity * (subscription.metadata?.privateRepos ?? 0),
          0,
        );
  const totalPrivate = Math.min(
    (privateCount ?? 0) + portalAllowance,
    MAX_SAFE,
  );
  const planDetail =
    plans?.find((plan) => plan.stripeId === currentPlan?.plan) ?? null;
  const planConfirmed =
    currentPlanIsFetchedAfterMount &&
    !currentPlanError &&
    isPlanChangeConfirmed(currentPlan, expectedPlan);

  return (
    <Stack hasGutter style={{maxWidth: '600px'}} data-testid="plan-information">
      <Alerts />
      {(checkoutResult === 'canceled' || planCheckoutResult === 'canceled') && (
        <Alert
          isLiveRegion
          isInline
          variant="info"
          title="Stripe Checkout canceled"
        >
          {planCheckoutResult === 'canceled' && (
            <Link
              to={`/organization/${encodeURIComponent(organizationName)}/plans`}
            >
              Choose a plan
            </Link>
          )}
        </Alert>
      )}
      {planReturned && (
        <Alert
          isLiveRegion
          isInline
          variant={planConfirmed ? 'success' : 'info'}
          data-testid="plan-change-result"
          title={
            planConfirmed
              ? 'Your subscription has been updated.'
              : checkingCheckout
                ? 'Checking your subscription with Quay…'
                : 'Your subscription has not been confirmed yet.'
          }
        >
          {!planConfirmed &&
            'Refresh this page to check again. Quay may still be processing your plan change.'}
        </Alert>
      )}
      {checkoutResult === 'returned' && (
        <Alert
          isLiveRegion
          isInline
          variant="info"
          title={
            checkingCheckout
              ? 'Refreshing your payment method from Quay…'
              : 'Returned from Stripe. Review your payment method below.'
          }
        />
      )}
      {currentPlan?.status === 'past_due' && (
        <Alert isLiveRegion variant="danger" title="Payment failed" isInline>
          Your last payment failed. Please update your payment method to avoid
          service interruption.
        </Alert>
      )}
      <Title headingLevel="h3">Current Plan</Title>
      <CurrentPlanSection
        currentPlan={currentPlan ?? null}
        planDetail={planDetail}
        isLoading={currentPlanIsLoading}
        isError={!!currentPlanError}
      />
      <Title headingLevel="h3">Usage</Title>
      <UsageSection
        privateCount={currentPlan?.usedPrivateRepos ?? 0}
        totalPrivate={totalPrivate}
        publicCount={publicCount}
        isLoading={currentPlanIsLoading}
        isError={!!currentPlanError}
      />
      <Title headingLevel="h3">Payment Method</Title>
      {stripeSetup.isError && (
        <Alert
          isLiveRegion
          isInline
          variant="danger"
          title="Unable to open Stripe Checkout. Please try again."
        >
          {getBillingErrorMessage(stripeSetup.error)}
        </Alert>
      )}
      <PaymentMethodSection
        card={card}
        isLoading={cardLoading}
        isError={cardError}
      />
      <ActionList>
        {(process.env.MOCK_API === 'true' || currentPlan?.hasSubscription) &&
          !cardLoading &&
          !cardError && (
            <ActionListItem>
              <Button
                variant="secondary"
                onClick={() => stripeSetup.mutate()}
                isLoading={stripeSetup.isLoading}
                isDisabled={stripeSetup.isLoading}
              >
                {card?.last4 ? 'Change payment method' : 'Add payment method'}
              </Button>
            </ActionListItem>
          )}
        <ActionListItem>
          <Button
            variant="secondary"
            onClick={() =>
              navigate(
                NavigationPath.organizationPlans.replace(
                  ':organizationName',
                  encodeURIComponent(organizationName),
                ),
              )
            }
          >
            Change Plan
          </Button>
        </ActionListItem>
      </ActionList>
      <MarketplaceDetails organizationName={organizationName} />
      <section aria-labelledby="billing-invoices-heading">
        <Title
          headingLevel="h3"
          id="billing-invoices-heading"
          className="pf-v6-u-mb-md"
        >
          Invoices
        </Title>
        <Flex
          alignItems={{default: 'alignItemsCenter'}}
          spaceItems={{default: 'spaceItemsSm'}}
          className="pf-v6-u-mb-md"
        >
          {invoicesLoading ? (
            <Skeleton
              width="100px"
              screenreaderText="Loading invoice summary"
            />
          ) : (
            <Content data-testid="invoice-summary">
              {invoicesError
                ? 'Unable to load invoices.'
                : `${invoices.length} ${
                    invoices.length === 1 ? 'invoice' : 'invoices'
                  }`}
            </Content>
          )}
          <Link
            to={NavigationPath.invoiceList.replace(
              ':organizationName',
              encodeURIComponent(organizationName),
            )}
          >
            View invoices
          </Link>
        </Flex>
        <Button
          variant="secondary"
          data-testid="invoice-settings-button"
          isDisabled={!settings}
          onClick={() => setInvoiceSettingsOpen(true)}
        >
          Invoice settings
        </Button>
      </section>
      {invoiceSettingsOpen && (
        <InvoiceSettingsModal
          organizationName={organizationName}
          isUserOrganization={isUserOrganization}
          enabled={settings?.invoice_email ?? false}
          email={settings?.invoice_email_address ?? settings?.email ?? ''}
          onClose={() => setInvoiceSettingsOpen(false)}
        />
      )}
    </Stack>
  );
};
