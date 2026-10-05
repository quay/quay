import {useEffect, useState} from 'react';
import {
  ActionGroup,
  Alert,
  Button,
  Checkbox,
  Flex,
  FlexItem,
  Form,
  FormAlert,
  FormGroup,
  FormHelperText,
  TextInput,
  Title,
} from '@patternfly/react-core';
import {useNavigate} from 'react-router-dom';
import {AxiosError} from 'axios';
import {useCurrentUser, useUpdateUser} from 'src/hooks/UseCurrentUser';
import {useOrganization} from 'src/hooks/UseOrganization';
import {useOrganizationSettings} from 'src/hooks/UseOrganizationSettings';
import {useRepositories} from 'src/hooks/UseRepositories';
import {useUpgradePlan} from 'src/hooks/UseUpgradePlan';
import {useCard} from 'src/hooks/UseCard';
import {AlertVariant, useUI} from 'src/contexts/UIContext';
import {NavigationPath} from 'src/routes/NavigationPath';
import Alerts from 'src/routes/Alerts';
import {CurrentPlanSection} from './CurrentPlanSection';
import {UsageSection} from './UsageSection';
import {PaymentMethodSection} from './PaymentMethodSection';
import MarketplaceDetails from './MarketplaceDetails';

type BillingInformationProps = {
  organizationName: string;
};

const MAX_SAFE = BigInt(Number.MAX_SAFE_INTEGER);

export const BillingInformation = ({organizationName}: BillingInformationProps) => {
  const navigate = useNavigate();
  const {user} = useCurrentUser();
  const {addAlert} = useUI();

  const {organization, isUserOrganization, loading} = useOrganization(organizationName);

  const {
    currentPlan,
    currentPlanIsLoading,
    currentPlanError,
    plans,
    privateAllowed,
    privateCount,
  } = useUpgradePlan(organizationName, !isUserOrganization);

  const {card, isLoading: cardLoading, isError: cardError} = useCard(
    organizationName,
    !isUserOrganization,
  );

  const {totalResults: publicCount} = useRepositories(organizationName, false);

  const usedPrivate = currentPlan?.usedPrivateRepos ?? 0;
  const [totalPrivate, setTotalPrivate] = useState(privateCount ?? 0);

  useEffect(() => {
    setTotalPrivate(privateCount ?? 0);
  }, [privateCount]);

  const {updateOrgSettings} = useOrganizationSettings({
    name: organizationName,
    onSuccess: () =>
      addAlert({title: 'Successfully updated settings', variant: AlertVariant.Success, key: 'alert'}),
    onError: (err) =>
      addAlert({title: err.response.data.error_message, variant: AlertVariant.Failure, key: 'alert'}),
  });

  const {updateUser, loading: userUpdateLoading, error: userUpdateError} = useUpdateUser({
    onSuccess: () =>
      addAlert({title: 'Successfully updated settings', variant: AlertVariant.Success, key: 'alert'}),
    onError: (err) =>
      addAlert({title: err.response.data.error_message, variant: AlertVariant.Failure, key: 'alert'}),
  });

  type validate = 'success' | 'warning' | 'error' | 'default';
  const [touched, setTouched] = useState(false);
  const [invoiceEmail, setInvoiceEmail] = useState(false);
  const [invoiceEmailAddress, setInvoiceEmailAddress] = useState('');
  const [validated, setValidated] = useState<validate>('success');

  useEffect(() => {
    resetFields();
  }, [loading]);

  const resetFields = () => {
    if (!loading && organization) {
      setInvoiceEmail(organization.invoice_email ?? false);
      setInvoiceEmailAddress(organization.invoice_email_address ?? '');
      setValidated(organization.invoice_email_address ? 'success' : 'default');
    } else if (isUserOrganization && user) {
      setInvoiceEmail(user.invoice_email ?? false);
      setInvoiceEmailAddress(user.invoice_email_address ?? '');
      setValidated(user.invoice_email_address ? 'success' : 'default');
    }
    setTouched(false);
  };

  // Look up full plan detail from the plans list for price and deprecated flag
  const planDetail = plans?.find((p) => p.stripeId === currentPlan?.plan) ?? null;

  const isPaymentFailed = currentPlan?.status === 'past_due';

  const totalPrivateDisplay =
    BigInt(totalPrivate) >= MAX_SAFE ? Number.MAX_SAFE_INTEGER : totalPrivate;

  return (
    <Form id="billing-form" style={{maxWidth: '600px'}}>
      <Alerts />

      {isPaymentFailed && (
        <FormAlert>
          <Alert variant="danger" title="Payment failed" isInline>
            Your last payment failed. Please update your payment method to avoid service
            interruption.
          </Alert>
        </FormAlert>
      )}

      {userUpdateError && (
        <FormAlert>
          <Alert
            variant="danger"
            title={
              (
                userUpdateError as AxiosError & {
                  response?: {data?: {error_message?: string}};
                }
              )?.response?.data?.error_message ?? 'An error occurred'
            }
            isInline
            aria-live="polite"
          />
        </FormAlert>
      )}

      <Title headingLevel="h3">Current Plan</Title>
      <CurrentPlanSection
        currentPlan={currentPlan ?? null}
        planDetail={planDetail}
        isLoading={currentPlanIsLoading}
        isError={!!currentPlanError}
      />

      <Title headingLevel="h3">Usage</Title>
      <UsageSection
        privateCount={usedPrivate}
        totalPrivate={totalPrivateDisplay}
        publicCount={publicCount}
        isLoading={currentPlanIsLoading}
        isError={!!currentPlanError}
      />

      <Title headingLevel="h3">Payment Method</Title>
      <PaymentMethodSection card={card} isLoading={cardLoading} isError={cardError} />

      <Flex>
        <FlexItem>
          <Button
            variant="secondary"
            onClick={() => navigate(NavigationPath.overviewList)}
          >
            Change Plan
          </Button>
        </FlexItem>
      </Flex>

      <MarketplaceDetails
        organizationName={organizationName}
        updateTotalPrivate={(mp) =>
          setTotalPrivate(mp + (privateCount ?? 0))
        }
      />

      <Title headingLevel="h3">Invoice Settings</Title>
      <FormGroup fieldId="checkbox">
        <Checkbox
          id="checkbox"
          data-testid="billing-receipts-checkbox"
          label="Send receipts via email"
          aria-label="Send receipts via email"
          isChecked={invoiceEmail}
          onChange={() => {
            setTouched(true);
            setInvoiceEmail((v) => !v);
          }}
        />
      </FormGroup>
      <FormGroup isInline label="Invoice Email" fieldId="form-email">
        <TextInput
          type="email"
          id="billing-settings-invoice-email"
          data-testid="billing-invoice-email"
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
        <FormHelperText>Invoices will be sent to this e-mail address.</FormHelperText>
      </FormGroup>

      <Button
        variant="link"
        isInline
        onClick={() => navigate(`/organization/${organizationName}/invoices`)}
      >
        View Invoices
      </Button>

      <ActionGroup>
        <Flex justifyContent={{default: 'justifyContentFlexEnd'}} width="100%">
          <Button
            variant="primary"
            id="save-billing-settings"
            data-testid="billing-save-button"
            isLoading={userUpdateLoading}
            isDisabled={!touched || validated === 'error'}
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
          <Button variant="link" onClick={() => resetFields()} isDisabled={!touched}>
            Cancel
          </Button>
        </Flex>
      </ActionGroup>
    </Form>
  );
};
