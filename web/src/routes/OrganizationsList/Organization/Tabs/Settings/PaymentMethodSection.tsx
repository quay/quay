import {Content, Flex, FlexItem, Skeleton} from '@patternfly/react-core';
import {CreditCardIcon} from '@patternfly/react-icons';
import {BillingCard} from 'src/resources/BillingResource';

type Props = {
  card: BillingCard | null;
  isLoading: boolean;
  isError: boolean;
};

export function PaymentMethodSection({card, isLoading, isError}: Props) {
  if (isLoading) {
    return (
      <Flex direction={{default: 'column'}} spaceItems={{default: 'spaceItemsSm'}}>
        <Skeleton data-testid="payment-method-skeleton" width="30%" />
        <Skeleton width="20%" />
      </Flex>
    );
  }

  if (isError) {
    return <Content>Unable to load payment method.</Content>;
  }

  if (!card?.last4) {
    return <Content>No payment method on file.</Content>;
  }

  return (
    <Flex spaceItems={{default: 'spaceItemsMd'}} alignItems={{default: 'alignItemsCenter'}}>
      <FlexItem>
        <CreditCardIcon />
      </FlexItem>
      <FlexItem>
        <Flex direction={{default: 'column'}} spaceItems={{default: 'spaceItemsNone'}}>
          <FlexItem>
            <Content>{card.type}</Content>
          </FlexItem>
          <FlexItem>
            <Content>••••{card.last4}</Content>
          </FlexItem>
          <FlexItem>
            <Content>
              {card.exp_month}/{card.exp_year}
            </Content>
          </FlexItem>
        </Flex>
      </FlexItem>
    </Flex>
  );
}
