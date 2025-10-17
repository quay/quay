import {useEffect, useState} from 'react';
import {
  Flex,
  FlexItem,
  Form,
  TextInput,
  ActionGroup,
  Button,
  Title,
  Checkbox,
  FormAlert,
  Alert,
  FormGroup,
  FormHelperText,
} from '@patternfly/react-core';
import {useRepositories} from 'src/hooks/UseRepositories';
import {useCurrentUser, useUpdateUser} from 'src/hooks/UseCurrentUser';
import {useOrganization} from 'src/hooks/UseOrganization';
import {useUpgradePlan} from 'src/hooks/UseUpgradePlan';
import {AxiosError} from 'axios';
import {useOrganizationSettings} from 'src/hooks/UseOrganizationSettings';
import {useAlerts} from 'src/hooks/UseAlerts';
import {AlertVariant} from 'src/atoms/AlertState';
import Alerts from 'src/routes/Alerts';
import MarketplaceDetails from './MarketplaceDetails';

type BillingInformationProps = {
  organizationName: string;
};

export const BillingInformation = (props: BillingInformationProps) => {
  const organizationName = props.organizationName;
  const {user} = useCurrentUser();
  const {addAlert} = useAlerts();
  const {
    updateUser,
    loading: userUpdateLoading,
    error: userUpdateError,
  } = useUpdateUser({
    onSuccess: () => {
      addAlert({
        title: 'Successfully updated settings',
        variant: AlertVariant.Success,
        key: 'alert',
      });
    },
    onError: (err) => {
      addAlert({
        title: err.response.data.error_message,
        variant: AlertVariant.Failure,
        key: 'alert',
      });
    },
  });

  const maxPrivate = BigInt(Number.MAX_SAFE_INTEGER);

  const [touched, setTouched] = useState(false);
  const [invoiceEmail, setInvoiceEmail] = useState(false);
  const [invoiceEmailAddress, setInvoiceEmailAddress] = useState('');

  type validate = 'success' | 'warning' | 'error' | 'default';
  const [validated, setValidated] = useState<validate>('success');

  const {organization, isUserOrganization, loading} =
    useOrganization(organizationName);

  const {updateOrgSettings} = useOrganizationSettings({
    name: organizationName,
    onSuccess: () => {
      addAlert({
        title: 'Successfully updated settings',
        variant: AlertVariant.Success,
        key: 'alert',
      });
    },
    onError: (err) => {
      addAlert({
        title: err.response.data.error_message,
        variant: AlertVariant.Failure,
        key: 'alert',
      });
    },
  });

  const {currentPlan, privateAllowed, privateCount, upgrade} = useUpgradePlan(
    organizationName,
    !isUserOrganization,
  );

  // total number of private repos allowed (stripe subscription + RH subscription watch)
  const [totalPrivate, setTotalPrivate] = useState(
    currentPlan?.usedPrivateRepos || 0,
  );

  const addMarketplacePrivate = (marketplacePrivate: number) => {
    const sum = marketplacePrivate + (currentPlan?.usedPrivateRepos || 0);
    setTotalPrivate(sum);
  };

  const error = userUpdateError;

  const updateLoading = userUpdateLoading;
  useEffect(() => {
    resetFields();
  }, [loading]);

  const resetFields = () => {
    if (!loading && organization) {
      setInvoiceEmail(organization.invoice_email || false);
      setInvoiceEmailAddress(organization.invoice_email_address || '');
      if (organization.invoice_email_address) {
        setValidated('success');
      } else {
        setValidated('default');
      }
    } else if (isUserOrganization && user) {
      setInvoiceEmail(user.invoice_email || false);
      setInvoiceEmailAddress(user.invoice_email_address || '');
      if (user.invoice_email_address) {
        setValidated('success');
      } else {
        setValidated('default');
      }
    }
    setTouched(false);
  };

  const {totalResults} = useRepositories(organizationName);

  return (
    <Form id="form-form" width="70%">
      {error && (
        <FormAlert>
          <Alert
            variant="danger"
            title={
              (
                error as AxiosError & {
                  response?: {data?: {error_message?: string}};
                }
              )?.response?.data?.error_message || 'An error occurred'
            }
            aria-live="polite"
            isInline
          />
        </FormAlert>
      )}
      <Flex
        spaceItems={{default: 'spaceItemsSm'}}
        direction={{default: 'column'}}
      >
        <FlexItem>
          <Title headingLevel="h3">
            {currentPlan?.plan.toUpperCase()} organization&apos;s plan
          </Title>
        </FlexItem>
        {privateAllowed ? (
          <FlexItem>{`${privateCount} of ${
            totalPrivate >= maxPrivate ? 'unlimited' : totalPrivate
          } private repositories used`}</FlexItem>
        ) : null}
        <FlexItem>{`${totalResults} of unlimited public repositories used`}</FlexItem>
      </Flex>

      <Flex width={'70%'}>
        <Button
          variant="secondary"
          isDisabled={true} // TODO: Enable when we have a payment processor
          onClick={async () => {
            await upgrade();
          }}
        >
          Change Plan
        </Button>
      </Flex>

      <FormGroup fieldId="checkbox">
        <Checkbox
          id="checkbox"
          label="Send receipts via email"
          aria-label="Send receipts via email"
          isChecked={invoiceEmail}
          onChange={() => {
            setTouched(true);
            setInvoiceEmail(!invoiceEmail);
          }}
        />
      </FormGroup>
      <FormGroup isInline label="Invoice Email" fieldId="form-email">
        <TextInput
          type="email"
          id="billing-settings-invoice-email"
          value={invoiceEmailAddress}
          onChange={(_, val) => {
            setTouched(true);
            setInvoiceEmailAddress(val);
            if (/^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i.test(val)) {
              setValidated('success');
            } else if (!val) {
              setValidated('default');
            } else {
              setValidated('error');
            }
          }}
        />
        <FormHelperText>
          Invoices will be sent to this e-mail address.
        </FormHelperText>
      </FormGroup>

      <Button
        variant="link"
        isInline
        isDisabled={true} // TODO: Enable when we have a payment processor
      >
        View Invoices
      </Button>

      <MarketplaceDetails
        organizationName={props.organizationName}
        updateTotalPrivate={addMarketplacePrivate}
      />

      <ActionGroup>
        <Flex
          justifyContent={{default: 'justifyContentFlexEnd'}}
          width={'100%'}
        >
          <Button
            variant="primary"
            id="save-billing-settings"
            isLoading={updateLoading}
            isDisabled={!touched || validated == 'error'}
            onClick={async (e) => {
              e.preventDefault();
              if (!isUserOrganization) {
                await updateOrgSettings({
                  invoice_email: invoiceEmail,
                  invoice_email_address: invoiceEmailAddress,
                });
              } else {
                await updateUser({
                  invoice_email: invoiceEmail,
                  invoice_email_address: invoiceEmailAddress,
                });
              }
            }}
          >
            Save
          </Button>
          <Button
            variant="link"
            onClick={() => resetFields()}
            isDisabled={!touched}
          >
            Cancel
          </Button>
        </Flex>
      </ActionGroup>
      <Alerts />
    </Form>
  );
};
