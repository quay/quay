import {
  Content,
  EmptyState,
  EmptyStateBody,
  Label,
  Spinner,
  Title,
} from '@patternfly/react-core';
import {Table, Tbody, Td, Th, Thead, Tr} from '@patternfly/react-table';
import {useInvoices} from 'src/hooks/UseInvoices';
import {useOrganization} from 'src/hooks/UseOrganization';

type Props = {organizationName: string};

export function InvoiceList({organizationName}: Props) {
  const {isUserOrganization} = useOrganization(organizationName);
  const {invoices, isLoading, isError} = useInvoices(
    organizationName,
    !isUserOrganization,
  );

  if (isLoading) {
    return <Spinner aria-label="Loading invoices" />;
  }

  if (isError) {
    return <Content>Unable to load invoices.</Content>;
  }

  if (invoices.length === 0) {
    return (
      <EmptyState titleText="No invoices" headingLevel="h3">
        <EmptyStateBody>No invoices found for this account.</EmptyStateBody>
      </EmptyState>
    );
  }

  return (
    <>
      <Title headingLevel="h2" className="pf-v6-u-mb-md">
        Invoices
      </Title>
      <Table aria-label="Invoice list">
        <Thead>
          <Tr>
            <Th>Date</Th>
            <Th>Period</Th>
            <Th>Amount</Th>
            <Th>Status</Th>
          </Tr>
        </Thead>
        <Tbody>
          {invoices.map((inv) => (
            <Tr key={inv.id}>
              <Td>{new Date(inv.date * 1000).toLocaleDateString()}</Td>
              <Td>
                {new Date(inv.period_start * 1000).toLocaleDateString()} -{' '}
                {new Date(inv.period_end * 1000).toLocaleDateString()}
              </Td>
              <Td>${(inv.total / 100).toFixed(2)}</Td>
              <Td>
                {inv.paid ? (
                  <Label color="green">Paid</Label>
                ) : (
                  <Label color="red">Unpaid</Label>
                )}
              </Td>
            </Tr>
          ))}
        </Tbody>
      </Table>
    </>
  );
}
