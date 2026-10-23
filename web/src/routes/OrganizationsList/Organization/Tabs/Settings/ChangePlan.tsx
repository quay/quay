import {useState} from 'react';
import {useNavigate} from 'react-router-dom';
import {useMutation, useQueryClient} from '@tanstack/react-query';
import {
  Alert,
  Button,
  Card,
  CardBody,
  CardFooter,
  CardTitle,
  Content,
  DescriptionList,
  DescriptionListGroup,
  DescriptionListTerm,
  DescriptionListDescription,
  Grid,
  GridItem,
  Modal,
  ModalBody,
  ModalFooter,
  ModalHeader,
  ModalVariant,
  Skeleton,
  Title,
} from '@patternfly/react-core';
import {useOrganization} from 'src/hooks/UseOrganization';
import {useUpgradePlan} from 'src/hooks/UseUpgradePlan';
import {
  createSubscriptionCheckoutSession,
  setSubscription,
} from 'src/resources/BillingResource';
import type {Plan} from 'src/resources/BillingResource';
import {
  formatPlanPrice,
  getAvailablePlans,
  getPlanChangeReturnPath,
  getPlanCheckoutReturnUrls,
  getPlanChangeAction,
  getBillingErrorMessage,
} from 'src/libs/billing';
import {BillingBreadcrumb} from './BillingBreadcrumb';
import {CurrentPlanSection} from './CurrentPlanSection';

type Props = {organizationName: string};

export function ChangePlan({organizationName}: Props) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const {isUserOrganization} = useOrganization(organizationName);
  const {
    currentPlan,
    currentPlanIsLoading,
    currentPlanError,
    plans,
    loading,
    errorFetchingPlanData,
  } = useUpgradePlan(organizationName, !isUserOrganization);
  const [pendingPlan, setPendingPlan] = useState<Plan | null>(null);
  const planDetail =
    plans.find((plan) => plan.stripeId === currentPlan?.plan) ?? null;
  const availablePlans = getAvailablePlans(
    plans,
    currentPlan?.plan,
    !isUserOrganization,
  );
  const isLoading = currentPlanIsLoading || loading;
  const isError = !!currentPlanError || !!errorFetchingPlanData;
  const checkout = useMutation({
    retry: false,
    mutationFn: (plan: Plan) => {
      return createSubscriptionCheckoutSession(
        plan.stripeId,
        getPlanCheckoutReturnUrls(
          organizationName,
          window.location.origin,
          plan.stripeId,
          window.location.pathname,
        ),
        isUserOrganization ? null : organizationName,
      );
    },
    onSuccess: (session) => window.location.assign(session.url),
  });
  const changePlan = useMutation({
    retry: false,
    mutationFn: (plan: Plan) => {
      return setSubscription(
        plan.stripeId,
        isUserOrganization ? null : organizationName,
      );
    },
    onSuccess: async (_result, plan) => {
      await Promise.all([
        queryClient.invalidateQueries([
          'organization',
          isUserOrganization ? null : organizationName,
          'plan',
        ]),
        queryClient.invalidateQueries(['privateallowed', organizationName]),
        queryClient.invalidateQueries(['card', organizationName]),
        queryClient.invalidateQueries(['invoices', organizationName]),
      ]);
      setPendingPlan(null);
      navigate(getPlanChangeReturnPath(organizationName, plan.stripeId));
    },
  });

  return (
    <>
      <BillingBreadcrumb
        organizationName={organizationName}
        currentPage="Choose a plan"
      />
      <Title headingLevel="h1" className="pf-v6-u-mb-sm">
        Choose a plan
      </Title>
      <Content className="pf-v6-u-mb-lg">
        Review your current plan and compare the available options.
      </Content>
      <Card className="pf-v6-u-mb-xl" data-testid="current-plan-card">
        <CardTitle>
          <Title
            headingLevel="h2"
            size="lg"
            className="pf-v6-u-text-align-start"
          >
            Current plan
          </Title>
        </CardTitle>
        <CardBody>
          <CurrentPlanSection
            currentPlan={currentPlan ?? null}
            planDetail={planDetail}
            isLoading={isLoading}
            isError={isError}
          />
          {!isLoading && !isError && currentPlan && (
            <DescriptionList
              columnModifier={{default: '1Col', md: '2Col'}}
              className="pf-v6-u-mt-lg"
            >
              <DescriptionListGroup>
                <DescriptionListTerm>Private repositories</DescriptionListTerm>
                <DescriptionListDescription>
                  {currentPlan.usedPrivateRepos} used
                  {planDetail ? ` of ${planDetail.privateRepos}` : ''}
                </DescriptionListDescription>
              </DescriptionListGroup>
              {currentPlan.currentPeriodEnd && (
                <DescriptionListGroup>
                  <DescriptionListTerm>
                    {currentPlan.status === 'trialing'
                      ? 'Trial ends'
                      : 'Next billing date'}
                  </DescriptionListTerm>
                  <DescriptionListDescription>
                    {new Date(
                      (currentPlan.trialEnd ?? currentPlan.currentPeriodEnd) *
                        1000,
                    ).toLocaleDateString()}
                  </DescriptionListDescription>
                </DescriptionListGroup>
              )}
            </DescriptionList>
          )}
        </CardBody>
      </Card>
      <Title headingLevel="h2" size="xl" className="pf-v6-u-mb-sm">
        Available plans
      </Title>
      <Content className="pf-v6-u-mb-lg">
        Select a plan to review and confirm your change.
      </Content>
      {checkout.isError && (
        <Alert
          isLiveRegion
          isInline
          variant="danger"
          title="Unable to open plan checkout. Please try again."
          className="pf-v6-u-mb-md"
        >
          {getBillingErrorMessage(checkout.error)}
        </Alert>
      )}
      {isLoading ? (
        <Skeleton height="240px" screenreaderText="Loading available plans" />
      ) : isError ? (
        <Alert
          isLiveRegion
          isInline
          variant="danger"
          title="Unable to load available plans"
        />
      ) : availablePlans.length === 0 ? (
        <Content>No other plans are available.</Content>
      ) : (
        <Grid hasGutter aria-label="Available plans">
          {availablePlans.map((plan) => (
            <GridItem key={plan.stripeId} span={12} md={6} xl={4}>
              <Card
                data-testid={`available-plan-${plan.stripeId}`}
                isFullHeight
              >
                <CardTitle>
                  <Title
                    headingLevel="h3"
                    size="lg"
                    className="pf-v6-u-text-align-start"
                  >
                    {plan.title}
                  </Title>
                </CardTitle>
                <CardBody>
                  <Title headingLevel="h4" size="2xl" className="pf-v6-u-mb-md">
                    {formatPlanPrice(plan.price)}
                  </Title>
                  <Content>
                    {plan.privateRepos === 0
                      ? 'No private repositories'
                      : `${plan.privateRepos} private repositories`}
                  </Content>
                  <Content>Unlimited public repositories</Content>
                  {plan.bus_features && (
                    <Content>Team management and audit logs</Content>
                  )}
                </CardBody>
                <CardFooter>
                  <Button
                    variant="primary"
                    isDisabled={
                      !currentPlan || checkout.isLoading || changePlan.isLoading
                    }
                    isLoading={
                      checkout.isLoading &&
                      checkout.variables?.stripeId === plan.stripeId
                    }
                    onClick={() => {
                      if (!currentPlan) return;
                      if (getPlanChangeAction(currentPlan, plan) === 'checkout')
                        checkout.mutate(plan);
                      else {
                        changePlan.reset();
                        setPendingPlan(plan);
                      }
                    }}
                  >
                    Select {plan.title}
                  </Button>
                </CardFooter>
              </Card>
            </GridItem>
          ))}
        </Grid>
      )}
      <Modal
        variant={ModalVariant.small}
        isOpen={!!pendingPlan}
        onClose={() => {
          if (!changePlan.isLoading) setPendingPlan(null);
        }}
        aria-labelledby="plan-change-title"
      >
        <ModalHeader title="Confirm plan change" labelId="plan-change-title" />
        <ModalBody>
          {changePlan.isError && (
            <Alert
              isLiveRegion
              isInline
              variant="danger"
              title="Unable to change your plan. Please try again."
              className="pf-v6-u-mb-md"
            >
              {getBillingErrorMessage(changePlan.error)}
            </Alert>
          )}
          Switch from <strong>{planDetail?.title ?? currentPlan?.plan}</strong>{' '}
          to <strong>{pendingPlan?.title}</strong> for{' '}
          {pendingPlan ? formatPlanPrice(pendingPlan.price) : ''}?
          {pendingPlan &&
            currentPlan?.usedPrivateRepos > pendingPlan.privateRepos && (
              <Alert
                isLiveRegion
                isInline
                variant="warning"
                title="This plan includes fewer private repositories than you currently use."
                className="pf-v6-u-mt-md"
              >
                Review your repository usage before confirming.
              </Alert>
            )}
        </ModalBody>
        <ModalFooter>
          <Button
            variant="primary"
            isLoading={changePlan.isLoading}
            isDisabled={changePlan.isLoading || !pendingPlan}
            onClick={() => changePlan.mutate(pendingPlan)}
          >
            Confirm change
          </Button>
          <Button
            variant="link"
            isDisabled={changePlan.isLoading}
            onClick={() => setPendingPlan(null)}
          >
            Cancel
          </Button>
        </ModalFooter>
      </Modal>
    </>
  );
}
