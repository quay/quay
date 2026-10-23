import {
  Content,
  Flex,
  FlexItem,
  Progress,
  Skeleton,
} from '@patternfly/react-core';

import {getPrivateRepositoryUsage} from 'src/libs/billing';

type Props = {
  privateCount: number;
  totalPrivate: number;
  publicCount: number;
  isLoading: boolean;
  isError: boolean;
};

export function UsageSection({
  privateCount,
  totalPrivate,
  publicCount,
  isLoading,
  isError,
}: Props) {
  if (isLoading) {
    return (
      <Flex
        direction={{default: 'column'}}
        spaceItems={{default: 'spaceItemsSm'}}
      >
        <Skeleton data-testid="usage-skeleton" width="60%" />
        <Skeleton width="50%" />
      </Flex>
    );
  }

  if (isError) {
    return <Content>Unable to load usage information.</Content>;
  }

  const usage = getPrivateRepositoryUsage(privateCount, totalPrivate);

  return (
    <Flex
      direction={{default: 'column'}}
      spaceItems={{default: 'spaceItemsSm'}}
    >
      <FlexItem>
        <Content>{usage.label}</Content>
        {!usage.isUnlimited && totalPrivate > 0 && (
          <Progress
            value={usage.value}
            valueText={usage.label}
            variant={usage.isOverLimit ? 'warning' : undefined}
            title="Private repository usage"
            aria-label="Private repository usage"
          />
        )}
      </FlexItem>
      <FlexItem>
        <Content>{`${publicCount} of unlimited public repositories used`}</Content>
      </FlexItem>
    </Flex>
  );
}
