import {useEffect, useState} from 'react';
import {
  Alert,
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

  useEffect(() => {
    if (checkoutResult !== 'returned') return;
    // Stripe's webhook may finish after Checkout redirects back to Quay.
    let refreshes = 0;
    const interval = window.setInterval(() => {
      void queryClient.invalidateQueries(['card', organizationName]);
      refreshes += 1;
      if (refreshes >= 5) window.clearInterval(interval);
    }, 2000);
    return () => window.clearInterval(interval);
  }, [checkoutResult, organizationName, queryClient]);

  const {
    currentPlan,
    currentPlanIsLoading,
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

  return (
    <Stack hasGutter style={{maxWidth: '600px'}} data-testid="plan-information">
      <Alerts />
      {currentPlan?.status === 'past_due' && (
        <Alert variant="danger" title="Payment failed" isInline>
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
          isInline
          variant="danger"
          title="Unable to open Stripe Checkout. Please try again."
        />
      )}
      <PaymentMethodSection
        card={card}
        isLoading={cardLoading}
        isError={cardError}
        isUpdating={stripeSetup.isLoading}
        onChange={
          process.env.MOCK_API === 'true' || currentPlan?.hasSubscription
            ? () => stripeSetup.mutate()
            : undefined
        }
      />
      <div>
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
      </div>
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
