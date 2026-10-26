import {useMemo, useState} from 'react';
import {
  Button,
  Content,
  EmptyState,
  EmptyStateBody,
  Flex,
  FlexItem,
  Label,
  Skeleton,
  SearchInput,
  Title,
} from '@patternfly/react-core';
import {DownloadIcon} from '@patternfly/react-icons';
import {Table, Tbody, Td, Th, Thead, Tr} from '@patternfly/react-table';
import {useInvoices} from 'src/hooks/UseInvoices';
import {useOrganization} from 'src/hooks/UseOrganization';
import {filterInvoices, formatInvoiceDate} from 'src/libs/billing';
import {BillingBreadcrumb} from './BillingBreadcrumb';

type Props = {organizationName: string};

export function InvoiceList({organizationName}: Props) {
  const {isUserOrganization} = useOrganization(organizationName);
  const {invoices, isLoading, isError} = useInvoices(
    organizationName,
    !isUserOrganization,
  );
  const [search, setSearch] = useState('');
  const visibleInvoices = useMemo(
    () => filterInvoices(invoices, search),
    [invoices, search],
  );
  // The preview archive contains the same PDFs supplied by the mock invoice list.
  const archiveUrl =
    process.env.MOCK_API === 'true' ? '/invoices/quay-invoices.zip' : undefined;

  return (
    <>
      <BillingBreadcrumb
        organizationName={organizationName}
        currentPage="Invoices"
      />
      <Title headingLevel="h1" className="pf-v6-u-mb-sm">
        Invoices
      </Title>
      <Content className="pf-v6-u-mb-lg">
        Search your billing history and download your invoices.
      </Content>
      <Flex
        direction={{default: 'column', md: 'row'}}
        justifyContent={{default: 'justifyContentSpaceBetween'}}
        alignItems={{md: 'alignItemsCenter'}}
        className="pf-v6-u-mb-md"
      >
        <FlexItem style={{width: '100%', maxWidth: '360px'}}>
          <SearchInput
            placeholder="Search invoices"
            aria-label="Search invoices"
            resetButtonLabel="Clear invoice search"
            data-testid="invoice-search"
            value={search}
            onChange={(_, value) => setSearch(value)}
            onClear={() => setSearch('')}
            isDisabled={isLoading || isError || invoices.length === 0}
          />
        </FlexItem>
        <FlexItem>
          <Button
            component="a"
            variant="primary"
            icon={<DownloadIcon />}
            href={archiveUrl}
            download={`quay-${organizationName}-invoices.zip`}
            isDisabled={
              isLoading || isError || invoices.length === 0 || !archiveUrl
            }
          >
            Download all invoices
          </Button>
        </FlexItem>
      </Flex>
      {!isLoading && !isError && invoices.length > 0 && (
        <Content
          aria-live="polite"
          data-testid="invoice-results-summary"
          className="pf-v6-u-mb-md"
        >
          {search.trim()
            ? `${visibleInvoices.length} of ${invoices.length} invoices`
            : `${invoices.length} invoices`}
        </Content>
      )}
      {isLoading ? (
        <Skeleton height="200px" screenreaderText="Loading invoices" />
      ) : isError ? (
        <Content>Unable to load invoices. Please try again later.</Content>
      ) : invoices.length === 0 ? (
        <EmptyState titleText="No invoices" headingLevel="h2">
          <EmptyStateBody>No invoices found for this account.</EmptyStateBody>
        </EmptyState>
      ) : visibleInvoices.length === 0 ? (
        <EmptyState titleText="No matching invoices" headingLevel="h2">
          <EmptyStateBody>
            No invoices match “{search.trim()}”. Try another keyword.
          </EmptyStateBody>
        </EmptyState>
      ) : (
        <Table aria-label="Invoice list">
          <Thead>
            <Tr>
              <Th>Date</Th>
              <Th>Period</Th>
              <Th>Amount</Th>
              <Th>Status</Th>
              <Th>Download</Th>
            </Tr>
          </Thead>
          <Tbody>
            {visibleInvoices.map((inv) => (
              <Tr key={inv.id}>
                <Td dataLabel="Date">{formatInvoiceDate(inv.date)}</Td>
                <Td dataLabel="Period">
                  {formatInvoiceDate(inv.period_start)} -{' '}
                  {formatInvoiceDate(inv.period_end)}
                </Td>
                <Td dataLabel="Amount">${(inv.total / 100).toFixed(2)}</Td>
                <Td dataLabel="Status">
                  <Label color={inv.paid ? 'green' : 'red'}>
                    {inv.paid ? 'Paid' : 'Unpaid'}
                  </Label>
                </Td>
                <Td dataLabel="Download">
                  <Button
                    component="a"
                    variant="link"
                    isInline
                    icon={<DownloadIcon />}
                    href={
                      inv.download_url ??
                      `${
                        process.env.QUAY_HOSTED === 'true'
                          ? 'https://quay.io'
                          : ''
                      }/receipt?id=${encodeURIComponent(inv.id)}`
                    }
                    target={
                      process.env.QUAY_HOSTED === 'true' ? '_blank' : undefined
                    }
                    rel="noopener noreferrer"
                    download={`quay-invoice-${inv.id}.pdf`}
                    aria-label={`Download PDF for invoice ${inv.id}`}
                  >
                    Download PDF
                  </Button>
                </Td>
              </Tr>
            ))}
          </Tbody>
        </Table>
      )}
    </>
  );
}
