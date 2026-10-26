import {
  Content,
  Flex,
  FlexItem,
  Label,
  Skeleton,
  Title,
} from '@patternfly/react-core';
import {
  Plan,
  Subscription,
  SubscriptionStatus,
} from 'src/resources/BillingResource';

type Props = {
  currentPlan: Subscription | null;
  planDetail: Plan | null;
  isLoading: boolean;
  isError: boolean;
};

function trialCountdown(trialEndTimestamp: number): string {
  const nowSeconds = Math.floor(Date.now() / 1000);
  const diffDays = Math.floor((trialEndTimestamp - nowSeconds) / 86400);
  return diffDays < 1 ? '< 1 day remaining' : `${diffDays} days remaining`;
}

function statusLabel(
  status: SubscriptionStatus | null,
  planDetail: Plan | null,
) {
  if (planDetail?.deprecated) {
    return <Label color="orange">Deprecated</Label>;
  }
  switch (status) {
    case 'trialing':
      return <Label color="blue">Trial</Label>;
    case 'past_due':
      return <Label color="red">Payment Failed</Label>;
    case 'active':
      return planDetail?.price === 0 ? (
        <Label color="grey">Free</Label>
      ) : (
        <Label color="green">Active</Label>
      );
    default:
      return null;
  }
}

export function CurrentPlanSection({
  currentPlan,
  planDetail,
  isLoading,
  isError,
}: Props) {
  if (isLoading) {
    return (
      <Flex
        direction={{default: 'column'}}
        spaceItems={{default: 'spaceItemsSm'}}
      >
        <Skeleton data-testid="current-plan-skeleton" width="40%" />
        <Skeleton width="25%" />
        <Skeleton width="15%" />
      </Flex>
    );
  }

  if (isError || !currentPlan) {
    return <Content>Unable to load plan information.</Content>;
  }

  const planTitle =
    planDetail?.title ??
    currentPlan.plan?.toUpperCase() ??
    currentPlan.plan ??
    '';
  const priceLabel =
    planDetail && planDetail.price > 0
      ? `$${(planDetail.price / 100).toFixed(0)}/month`
      : null;

  return (
    <Flex
      direction={{default: 'column'}}
      spaceItems={{default: 'spaceItemsSm'}}
    >
      <FlexItem>
        <Flex
          spaceItems={{default: 'spaceItemsMd'}}
          alignItems={{default: 'alignItemsCenter'}}
        >
          <FlexItem>
            <Title headingLevel="h3">{planTitle}</Title>
          </FlexItem>
          <FlexItem>{statusLabel(currentPlan.status, planDetail)}</FlexItem>
        </Flex>
      </FlexItem>
      {priceLabel && (
        <FlexItem>
          <Content>{priceLabel}</Content>
        </FlexItem>
      )}
      {currentPlan.status === 'trialing' && currentPlan.trialEnd && (
        <FlexItem>
          <Content>{trialCountdown(currentPlan.trialEnd)}</Content>
        </FlexItem>
      )}
    </Flex>
  );
}
