import {
  Alert,
  Button,
  Form,
  FormGroup,
  MenuToggle,
  MenuToggleElement,
  NumberInput,
  Select,
  SelectList,
  SelectOption,
  Modal,
  ModalVariant,
  ModalHeader,
  ModalBody,
  ModalFooter,
} from '@patternfly/react-core';
import React, {useState} from 'react';
import {AlertVariant, useUI} from 'src/contexts/UIContext';
import {useManageOrgSubscriptions} from 'src/hooks/UseMarketplaceSubscriptions';
import type {MarketplaceSubscription} from 'src/resources/BillingResource';

interface OrgSubscriptionModalProps {
  modalType: 'attach' | 'remove';
  org: string;
  subscriptions: MarketplaceSubscription[];
  isOpen: boolean;
  handleModalToggle: () => void;
}

export default function OrgSubscriptionModal(props: OrgSubscriptionModalProps) {
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [menuIsOpen, setMenuIsOpen] = useState(false);
  const [bindingQuantity, setBindingQuantity] = useState(1);
  const selected =
    selectedIndex == null ? null : props.subscriptions[selectedIndex];
  const {addAlert} = useUI();
  const {manageSubscription, errorManageSubscription, loading} =
    useManageOrgSubscriptions(props.org, {
      onSuccess: () => {
        addAlert({
          variant: AlertVariant.Success,
          title: `Successfully ${
            props.modalType === 'attach' ? 'attached' : 'removed'
          } subscription`,
        });
        props.handleModalToggle();
      },
    });
  const close = () => {
    if (!loading) props.handleModalToggle();
  };

  return (
    <Modal
      variant={ModalVariant.small}
      isOpen={props.isOpen}
      onClose={close}
      aria-labelledby="subscription-modal-title"
    >
      <ModalHeader
        title={
          props.modalType === 'attach'
            ? 'Attach subscription'
            : 'Remove subscription'
        }
        labelId="subscription-modal-title"
      />
      <ModalBody>
        <Form>
          {errorManageSubscription && (
            <Alert
              isInline
              isLiveRegion
              variant="danger"
              title="Unable to update subscriptions. Please try again."
            />
          )}
          <FormGroup label="Subscription" fieldId="subscription-select-toggle">
            <Select
              isOpen={menuIsOpen}
              popperProps={{appendTo: 'inline'}}
              selected={selectedIndex}
              shouldFocusToggleOnSelect
              shouldFocusFirstItemOnOpen
              toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
                <MenuToggle
                  id="subscription-select-toggle"
                  data-testid="subscription-select-toggle"
                  aria-label="Select subscription"
                  ref={toggleRef}
                  isDisabled={loading}
                  onClick={() => setMenuIsOpen(!menuIsOpen)}
                  isExpanded={menuIsOpen}
                >
                  {selected
                    ? `${selected.quantity}x ${selected.sku} (${
                        selected.subscription_id ?? selected.id
                      })`
                    : 'Select subscription'}
                </MenuToggle>
              )}
              onSelect={(_, value) => {
                setSelectedIndex(Number(value));
                setBindingQuantity(1);
                setMenuIsOpen(false);
              }}
              onOpenChange={setMenuIsOpen}
            >
              <SelectList>
                {props.subscriptions.map((subscription, index) => (
                  <SelectOption key={subscription.id} value={index}>
                    {subscription.quantity}x {subscription.sku} (
                    {subscription.subscription_id ?? subscription.id})
                  </SelectOption>
                ))}
              </SelectList>
            </Select>
          </FormGroup>
          {selected?.sku === 'MW02702' && props.modalType === 'attach' && (
            <FormGroup label="Quantity" fieldId="subscription-binding-quantity">
              <NumberInput
                inputProps={{id: 'subscription-binding-quantity'}}
                inputAriaLabel="Quantity"
                minusBtnAriaLabel="Decrease quantity"
                plusBtnAriaLabel="Increase quantity"
                value={bindingQuantity}
                isDisabled={loading}
                onPlus={() =>
                  setBindingQuantity(
                    Math.min(bindingQuantity + 1, selected.quantity),
                  )
                }
                onMinus={() =>
                  setBindingQuantity(Math.max(bindingQuantity - 1, 1))
                }
                onChange={(event) =>
                  setBindingQuantity(
                    Number((event.target as HTMLInputElement).value),
                  )
                }
                min={1}
                max={selected.quantity}
              />
            </FormGroup>
          )}
        </Form>
      </ModalBody>
      <ModalFooter>
        <Button
          variant="primary"
          isLoading={loading}
          isDisabled={
            !selected ||
            loading ||
            (selected.sku === 'MW02702' &&
              (bindingQuantity < 1 ||
                bindingQuantity > selected.quantity ||
                !Number.isInteger(bindingQuantity)))
          }
          onClick={() =>
            manageSubscription({
              subscription: selected,
              manageType: props.modalType,
              bindingQuantity:
                props.modalType === 'attach' && selected.sku === 'MW02702'
                  ? bindingQuantity
                  : null,
            })
          }
        >
          Confirm
        </Button>
        <Button variant="link" onClick={close} isDisabled={loading}>
          Cancel
        </Button>
      </ModalFooter>
    </Modal>
  );
}
