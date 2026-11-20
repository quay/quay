import {Content, Flex, FlexItem, Progress, Skeleton} from '@patternfly/react-core';

const MAX_SAFE = BigInt(Number.MAX_SAFE_INTEGER);

type Props = {
  privateCount: number;
  totalPrivate: number;
  publicCount: number;
  isLoading: boolean;
  isError: boolean;
};

export function UsageSection({privateCount, totalPrivate, publicCount, isLoading, isError}: Props) {
  if (isLoading) {
    return (
      <Flex direction={{default: 'column'}} spaceItems={{default: 'spaceItemsSm'}}>
        <Skeleton data-testid="usage-skeleton" width="60%" />
        <Skeleton width="50%" />
      </Flex>
    );
  }

  if (isError) {
    return <Content>Unable to load usage information.</Content>;
  }

  const isUnlimited = BigInt(totalPrivate) >= MAX_SAFE;
  const privateLabel = isUnlimited
    ? `${privateCount} of unlimited private repositories used`
    : `${privateCount} of ${totalPrivate} private repositories used`;
  const progressValue =
    isUnlimited || totalPrivate === 0 ? 0 : (privateCount / totalPrivate) * 100;

  return (
    <Flex direction={{default: 'column'}} spaceItems={{default: 'spaceItemsSm'}}>
      <FlexItem>
        <Content>{privateLabel}</Content>
        {!isUnlimited && totalPrivate > 0 && (
          <Progress
            value={progressValue}
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
