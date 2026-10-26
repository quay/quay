import {useState} from 'react';
import {
  Alert,
  Button,
  Content,
  EmptyState,
  EmptyStateBody,
  Flex,
  Skeleton,
  Title,
} from '@patternfly/react-core';
import {Table, Tbody, Td, Th, Thead, Tr} from '@patternfly/react-table';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
import {useOrganization} from 'src/hooks/UseOrganization';
import {useMarketplaceSubscriptions} from 'src/hooks/UseMarketplaceSubscriptions';
import OrgSubscriptionModal from 'src/components/modals/OrgSubscriptionModal';
import {BillingBreadcrumb} from './BillingBreadcrumb';

export function SubscriptionList({
  organizationName,
}: {
  organizationName: string;
}) {
  const {user} = useCurrentUser();
  const {organization} = useOrganization(organizationName);
  const {userSubscriptions, orgSubscriptions, loading, error, enabled} =
    useMarketplaceSubscriptions(organizationName, user?.username);
  const isPersonal = organizationName === user?.username;
  const subscriptions = isPersonal ? userSubscriptions : orgSubscriptions;
  const [modalType, setModalType] = useState<'attach' | 'remove' | null>(null);
  const attachable = userSubscriptions.filter(
    (subscription) => subscription.assigned_to_org == null,
  );

  return (
    <>
      <BillingBreadcrumb
        organizationName={organizationName}
        currentPage="Subscriptions"
      />
      <Title headingLevel="h1" className="pf-v6-u-mb-sm">
        Subscriptions from Red Hat Customer Portal
      </Title>
      <Content className="pf-v6-u-mb-lg">
        {isPersonal
          ? 'View all subscriptions for your account and their namespace assignments.'
          : `View subscriptions attached to ${organizationName}.`}
      </Content>
      {enabled && !isPersonal && organization?.is_admin && (
        <Flex className="pf-v6-u-mb-lg">
          <Button
            variant="primary"
            onClick={() => setModalType('attach')}
            isDisabled={loading || error || attachable.length === 0}
          >
            Attach subscriptions
          </Button>
          <Button
            variant="secondary"
            onClick={() => setModalType('remove')}
            isDisabled={loading || error || subscriptions.length === 0}
          >
            Remove subscriptions
          </Button>
        </Flex>
      )}
      {loading ? (
        <Skeleton height="200px" screenreaderText="Loading subscriptions" />
      ) : error ? (
        <Alert
          isInline
          variant="danger"
          title="Unable to load subscriptions. Please try again later."
        />
      ) : !enabled ? (
        <Content>Customer Portal subscriptions are unavailable.</Content>
      ) : subscriptions.length === 0 ? (
        <EmptyState titleText="No subscriptions" headingLevel="h2">
          <EmptyStateBody>
            No Customer Portal subscriptions found for this namespace.
          </EmptyStateBody>
        </EmptyState>
      ) : (
        <Table
          aria-label="Customer Portal subscriptions"
          data-testid="subscription-list"
        >
          <Thead>
            <Tr>
              <Th>Subscription ID</Th>
              <Th>SKU</Th>
              <Th>Quantity</Th>
              <Th>Namespace</Th>
              <Th>Private repositories</Th>
            </Tr>
          </Thead>
          <Tbody>
            {subscriptions.map((subscription) => (
              <Tr
                key={subscription.id}
                data-testid={`subscription-row-${
                  subscription.subscription_id ?? subscription.id
                }`}
              >
                <Td dataLabel="Subscription ID">
                  {subscription.subscription_id ?? subscription.id}
                </Td>
                <Td dataLabel="SKU">{subscription.sku}</Td>
                <Td dataLabel="Quantity">{subscription.quantity}</Td>
                <Td dataLabel="Namespace">
                  {isPersonal
                    ? (subscription.assigned_to_org ?? user?.username)
                    : organizationName}
                </Td>
                <Td dataLabel="Private repositories">
                  {subscription.metadata?.privateRepos == null
                    ? 'Unavailable'
                    : subscription.quantity *
                      subscription.metadata.privateRepos}
                </Td>
              </Tr>
            ))}
          </Tbody>
        </Table>
      )}
      {modalType && (
        <OrgSubscriptionModal
          modalType={modalType}
          org={organizationName}
          subscriptions={modalType === 'attach' ? attachable : orgSubscriptions}
          isOpen
          handleModalToggle={() => setModalType(null)}
        />
      )}
    </>
  );
}
