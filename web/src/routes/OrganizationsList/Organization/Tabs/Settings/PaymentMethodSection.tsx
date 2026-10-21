import {Content, Flex, FlexItem, Label, Skeleton} from '@patternfly/react-core';
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
      <Flex
        direction={{default: 'column'}}
        spaceItems={{default: 'spaceItemsSm'}}
      >
        <Skeleton data-testid="payment-method-skeleton" width="30%" />
        <Skeleton width="20%" />
      </Flex>
    );
  }

  if (isError) {
    return <Content>Unable to load payment method.</Content>;
  }

  if (!card?.last4) {
    return (
      <Flex direction={{default: 'column'}}>
        <FlexItem>
          <Content>No payment method on file.</Content>
        </FlexItem>
      </Flex>
    );
  }

  return (
    <Flex
      direction={{default: 'column'}}
      spaceItems={{default: 'spaceItemsMd'}}
      data-testid="stored-payment-method"
    >
      <Flex
        spaceItems={{default: 'spaceItemsMd'}}
        alignItems={{default: 'alignItemsCenter'}}
      >
        <FlexItem>
          <CreditCardIcon />
        </FlexItem>
        <FlexItem>
          <Flex
            direction={{default: 'column'}}
            spaceItems={{default: 'spaceItemsNone'}}
          >
            <FlexItem>
              <Flex alignItems={{default: 'alignItemsCenter'}}>
                <FlexItem>
                  <Content>{card.type}</Content>
                </FlexItem>
                <FlexItem>
                  <Label>Default</Label>
                </FlexItem>
              </Flex>
            </FlexItem>
            <FlexItem>
              <Content>•••• {card.last4}</Content>
            </FlexItem>
            <FlexItem>
              <Content>{card.owner}</Content>
            </FlexItem>
            <FlexItem>
              <Content>
                Expires {String(card.exp_month).padStart(2, '0')}/
                {card.exp_year}
              </Content>
            </FlexItem>
          </Flex>
        </FlexItem>
      </Flex>
    </Flex>
  );
}
