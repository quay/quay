import {
  Button,
  Flex,
  FlexItem,
  HelperText,
  List,
  ListItem,
  Spinner,
  Title,
} from '@patternfly/react-core';
import React, {useEffect} from 'react';
import RequestError from 'src/components/errors/RequestError';
import OrgSubscriptionModal from 'src/components/modals/OrgSubscriptionModal';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
import {useMarketplaceSubscriptions} from 'src/hooks/UseMarketplaceSubscriptions';

type MarketplaceDetailsProps = {
  organizationName: string;
  updateTotalPrivate: (total: number) => void;
};

export default function MarketplaceDetails(props: MarketplaceDetailsProps) {
  const organizationName = props.organizationName;
  const {user} = useCurrentUser();
  const {userSubscriptions, orgSubscriptions, loading, error} =
    useMarketplaceSubscriptions(organizationName, user.username);

  const [isModalOpen, setIsModalOpen] = React.useState(false);
  const [modalType, setModalType] = React.useState('attach');

  useEffect(() => {
    if (loading) return;
    if (error) return;

    let marketplaceTotalPrivate = 0;
    if (organizationName != user.username) {
      for (let i = 0; i < orgSubscriptions.length; i++) {
        marketplaceTotalPrivate +=
          orgSubscriptions[i]['quantity'] *
          orgSubscriptions[i]['metadata']['privateRepos'];
      }
    } else {
      for (let i = 0; i < userSubscriptions.length; i++) {
        if (userSubscriptions[i]['assigned_to_org'] === null) {
          marketplaceTotalPrivate +=
            userSubscriptions[i]['quantity'] *
            userSubscriptions[i]['metadata']['privateRepos'];
        }
      }
    }
    props.updateTotalPrivate(marketplaceTotalPrivate);
  });

  const handleModalToggle = (modalType: string) => {
    setModalType(modalType);
    setIsModalOpen(!isModalOpen);
  };

  if (loading) {
    return <Spinner size="md" />;
  }

  if (error) {
    return (
      <>
        <Title headingLevel="h3">
          Subscriptions From Red Hat Customer Portal
        </Title>
        <RequestError message="Unable to load marketplace information" />
      </>
    );
  }

  if (user.username == organizationName) {
    return (
      <>
        <Title headingLevel="h3">
          Subscriptions From Red Hat Customer Portal
        </Title>
        <Flex id="user-subscription-list">
          <FlexItem>
            {userSubscriptions.map((subscription: Dict<string>) => (
              <HelperText key={subscription.id}>
                {subscription.quantity}x {subscription.sku}
                {subscription.assigned_to_org
                  ? ` attached to ${subscription.assigned_to_org}`
                  : ' belonging to user namespace'}
              </HelperText>
            ))}
          </FlexItem>
        </Flex>
      </>
    );
  }

  return (
    <>
      <Title headingLevel="h3">
        Subscriptions From Red Hat Customer Portal
      </Title>
      <Flex id="org-subscription-list">
        <FlexItem>
          {orgSubscriptions.map((subscription: Dict<string>) => (
            <HelperText key={subscription.id}>
              {subscription.quantity}x {subscription.sku} attached
            </HelperText>
          ))}
        </FlexItem>
      </Flex>
      <Flex>
        <FlexItem>
          <Button
            id="attach-subscription-button"
            variant="primary"
            onClick={() => {
              handleModalToggle('attach');
            }}
          >
            Attach Subscriptions
          </Button>
        </FlexItem>
        <FlexItem>
          <Button
            id="remove-subscription-button"
            variant="secondary"
            onClick={() => {
              handleModalToggle('remove');
            }}
          >
            Remove Subscriptions
          </Button>
        </FlexItem>
      </Flex>
      <OrgSubscriptionModal
        modalType={modalType}
        org={organizationName}
        subscriptions={
          modalType === 'attach'
            ? userSubscriptions.filter(
                (sub: Dict<string>) => sub.assigned_to_org === null,
              )
            : orgSubscriptions
        }
        isOpen={isModalOpen}
        handleModalToggle={handleModalToggle}
      />
    </>
  );
}
