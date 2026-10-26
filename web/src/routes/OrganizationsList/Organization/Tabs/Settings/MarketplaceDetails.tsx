import {Content, Flex, Skeleton, Title} from '@patternfly/react-core';
import {Link} from 'react-router-dom';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
import {useMarketplaceSubscriptions} from 'src/hooks/UseMarketplaceSubscriptions';
import {NavigationPath} from 'src/routes/NavigationPath';

export default function MarketplaceDetails({
  organizationName,
}: {
  organizationName: string;
}) {
  const {user} = useCurrentUser();
  const {userSubscriptions, orgSubscriptions, loading, error, enabled} =
    useMarketplaceSubscriptions(organizationName, user?.username);
  const subscriptions =
    organizationName === user?.username ? userSubscriptions : orgSubscriptions;

  return (
    <section aria-labelledby="portal-subscriptions-heading">
      <Title
        headingLevel="h3"
        id="portal-subscriptions-heading"
        className="pf-v6-u-mb-md"
      >
        Subscriptions from Red Hat Customer Portal
      </Title>
      <Flex
        alignItems={{default: 'alignItemsCenter'}}
        spaceItems={{default: 'spaceItemsSm'}}
      >
        {loading ? (
          <Skeleton width="140px" screenreaderText="Loading subscriptions" />
        ) : (
          <Content data-testid="subscription-summary">
            {!enabled
              ? 'Customer Portal subscriptions are unavailable.'
              : error
                ? 'Unable to load subscriptions.'
                : `${subscriptions.length} ${
                    subscriptions.length === 1
                      ? 'subscription'
                      : 'subscriptions'
                  }`}
          </Content>
        )}
        <Link
          to={NavigationPath.subscriptionList.replace(
            ':organizationName',
            encodeURIComponent(organizationName),
          )}
        >
          View subscriptions
        </Link>
      </Flex>
    </section>
  );
}
