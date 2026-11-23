import {useState} from 'react';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {
  Alert,
  Button,
  Card,
  CardBody,
  Content,
  Flex,
  FlexItem,
  Label,
  Modal,
  ModalBody,
  ModalFooter,
  ModalHeader,
  ModalVariant,
  Radio,
  Skeleton,
  Stack,
  StackItem,
} from '@patternfly/react-core';
import {CreditCardIcon, PlusCircleIcon} from '@patternfly/react-icons';
import {AlertVariant, useUI} from 'src/contexts/UIContext';
import {useStripeCardSetup} from 'src/hooks/UseStripeCardSetup';
import {
  fetchPrototypePaymentMethods,
  selectPrototypePaymentMethod,
} from 'src/resources/PrototypeBillingResource';

type Props = {namespace: string; isOrg: boolean; onClose: () => void};

export function PaymentMethodDialog({namespace, isOrg, onClose}: Props) {
  const org = isOrg ? namespace : null;
  const queryClient = useQueryClient();
  const {addAlert} = useUI();
  const stripeSetup = useStripeCardSetup(namespace, isOrg);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const {data, isLoading, isError, refetch} = useQuery(
    ['prototype-payment-methods', namespace],
    () => fetchPrototypePaymentMethods(org),
    {enabled: process.env.MOCK_API === 'true', retry: false},
  );
  const selection = selectedId ?? data?.defaultId;
  const change = useMutation({
    mutationFn: (id: string) => selectPrototypePaymentMethod(id, org),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries(['card', namespace]),
        queryClient.invalidateQueries(['prototype-payment-methods', namespace]),
      ]);
      addAlert({
        title: 'Payment method updated',
        variant: AlertVariant.Success,
        key: 'payment-method-change',
      });
      onClose();
    },
  });
  const busy = change.isLoading || stripeSetup.isLoading;
  return (
    <Modal
      isOpen
      variant={ModalVariant.small}
      onClose={() => {
        if (!busy) onClose();
      }}
      aria-labelledby="payment-method-title"
    >
      <ModalHeader
        title="Select saved payment method"
        labelId="payment-method-title"
      />
      <ModalBody>
        <Stack hasGutter>
          {(change.isError || stripeSetup.isError) && (
            <StackItem>
              <Alert
                isInline
                variant="danger"
                title="Unable to update your payment method. Please try again."
              />
            </StackItem>
          )}
          <StackItem>
            <Content>
              Select the payment method to use for your subscription.
            </Content>
          </StackItem>
          {isLoading ? (
            <StackItem>
              <Skeleton
                height="150px"
                screenreaderText="Loading saved payment methods"
              />
            </StackItem>
          ) : isError ? (
            <StackItem>
              <Alert
                isInline
                variant="danger"
                title="Unable to load saved payment methods"
              >
                <Button variant="link" isInline onClick={() => refetch()}>
                  Try again
                </Button>
              </Alert>
            </StackItem>
          ) : (
            <>
              <StackItem>
                <Stack
                  hasGutter
                  role="group"
                  aria-label="Saved payment methods"
                >
                  {data?.methods.length === 0 && (
                    <Content>No saved payment methods.</Content>
                  )}
                  {data?.methods.map((method) => (
                    <StackItem key={method.id}>
                      <Card isCompact>
                        <CardBody>
                          <Radio
                            id={`payment-method-${method.id}`}
                            name="saved-payment-method"
                            isChecked={selection === method.id}
                            isDisabled={busy}
                            onChange={() => {
                              setSelectedId(method.id);
                              change.reset();
                            }}
                            label={
                              <Flex
                                alignItems={{default: 'alignItemsCenter'}}
                                spaceItems={{default: 'spaceItemsSm'}}
                              >
                                <FlexItem>
                                  <CreditCardIcon />
                                </FlexItem>
                                <FlexItem>
                                  {method.type} ending in {method.last4}
                                </FlexItem>
                                {data.defaultId === method.id && (
                                  <FlexItem>
                                    <Label>Default</Label>
                                  </FlexItem>
                                )}
                              </Flex>
                            }
                            description={`${method.owner} · Expires ${String(
                              method.exp_month,
                            ).padStart(2, '0')}/${method.exp_year}`}
                          />
                        </CardBody>
                      </Card>
                    </StackItem>
                  ))}
                </Stack>
              </StackItem>
              <StackItem>
                <Button
                  variant="link"
                  isInline
                  icon={<PlusCircleIcon />}
                  isLoading={stripeSetup.isLoading}
                  isDisabled={busy}
                  onClick={() => stripeSetup.mutate()}
                >
                  Add payment method
                </Button>
              </StackItem>
            </>
          )}
        </Stack>
      </ModalBody>
      <ModalFooter>
        <Button
          variant="primary"
          isLoading={change.isLoading}
          isDisabled={
            busy ||
            isLoading ||
            isError ||
            !selection ||
            selection === data?.defaultId
          }
          onClick={() => {
            if (selection) change.mutate(selection);
          }}
        >
          Save payment method
        </Button>
        <Button variant="link" isDisabled={busy} onClick={onClose}>
          Cancel
        </Button>
      </ModalFooter>
    </Modal>
  );
}
