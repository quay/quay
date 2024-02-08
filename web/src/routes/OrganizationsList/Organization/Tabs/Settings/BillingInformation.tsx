import {useEffect, useState, ReactNode} from 'react';
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
  Radio,
  FormGroup,
  AlertActionLink,
  HelperText,
  AlertGroup,
  FormHelperText,
  NumberInput,
  Select,
  MenuToggleElement,
  MenuToggle,
} from '@patternfly/react-core';
import {useRepositories} from 'src/hooks/UseRepositories';
import {useCurrentUser, useUpdateUser} from 'src/hooks/UseCurrentUser';
import {useOrganization} from 'src/hooks/UseOrganization';
import {useUpgradePlan} from 'src/hooks/UseUpgradePlan';
import {AxiosError} from 'axios';
import {UserConvertConflictsModal} from 'src/components/modals/UserConvertConflictsModal';
import {useConvertAccount} from 'src/hooks/UseConvertAccount';
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
    onSuccess: (result) => {
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
  const [convertConflictModalOpen, setConvertConflictModalOpen] =
    useState(false);

  const [adminUser, setAdminUser] = useState('');
  const [adminPassword, setAdminPassword] = useState('');

  type validate = 'success' | 'warning' | 'error' | 'default';
  const [validated, setValidated] = useState<validate>('success');

  const {organization, isUserOrganization, loading} =
    useOrganization(organizationName);

  const {updateOrgSettings} = useOrganizationSettings({
    name: organizationName,
    onSuccess: (result) => {
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

  const [accountType, setAccountType] = useState(
    isUserOrganization ? 'individual' : 'organization',
  );
  useEffect(() => {
    setAccountType(isUserOrganization ? 'individual' : 'organization');
  }, [loading]);
  const {currentPlan, privateAllowed, privateCount, upgrade} = useUpgradePlan(
    organizationName,
    accountType == 'organization',
  );

  // total number of private repos allowed (stripe subscription + RH subscription watch)
  const [totalPrivate, setTotalPrivate] = useState(
    currentPlan?.privateRepos || 0,
  );

  const addMarketplacePrivate = (marketplacePrivate: number) => {
    const sum = marketplacePrivate + (currentPlan?.privateRepos || 0);
    setTotalPrivate(sum);
  };

  const {
    convert,
    loading: convertAccountLoading,
    error: convertAccountError,
  } = useConvertAccount({
    onSuccess: (result) => {
      addAlert({
        title: 'Successfully converted account',
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

  const error = userUpdateError || convertAccountError;

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
    } else if (isUserOrganization) {
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
            title={((error as AxiosError).response.data as any).error_message}
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
          label="Send receipts via email."
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

      {isUserOrganization && (
        <>
          <Title headingLevel="h3">Account Type</Title>
          <Radio
            id="radio-individual"
            label="Individual Account"
            name="radio-individual"
            isChecked={accountType == 'individual'}
            onClick={() => setAccountType('individual')}
            description="Single account with multiple repositories"
          />
          <Radio
            id="radio-organization"
            label="Organization Account"
            name="radio-organization"
            onClick={() => setAccountType('organization')}
            isChecked={accountType == 'organization'}
            description="Multiple users and teams that share access and billing under a single namespace"
          />
          {user.organizations.length > 0 && accountType == 'organization' && (
            <Alert
              isInline
              variant="warning"
              title="Unable to convert to organization account"
              actionLinks={
                <>
                  <AlertActionLink
                    onClick={() => setConvertConflictModalOpen(true)}
                  >
                    View details
                  </AlertActionLink>
                </>
              }
            >
              <p>
                This account cannot be converted into an organization, as it is
                already a member of one or many organizations.
              </p>
            </Alert>
          )}
          {!user.organizations.length && accountType == 'organization' && (
            <>
              <Alert
                isInline
                variant="info"
                title="Converting to organization account"
                actionLinks={
                  <>
                    <AlertActionLink
                      onClick={() => setConvertConflictModalOpen(true)}
                    >
                      View details
                    </AlertActionLink>
                  </>
                }
              >
                <p>
                  Fill out the form below to convert your current user account
                  into an organization. Your existing repositories will be
                  maintained under the namespace. All direct permissions
                  delegated to quayusername will be deleted.
                </p>
              </Alert>
              <Form maxWidth="50%" style={{paddingLeft: '30px'}}>
                <Title headingLevel="h3">Admin User</Title>
                <HelperText>
                  The username and password for the account that will become an
                  administrator of the organization. Note that this account must
                  be a seperate registered account from the account that you are
                  trying to convert, and must already exist
                </HelperText>
                <FormGroup
                  isInline
                  label="Admin Username"
                  fieldId="form-organization"
                >
                  <TextInput
                    type="text"
                    id="form-name"
                    onChange={(_, val) => {
                      setAdminUser(val);
                    }}
                    value={adminUser}
                  />
                </FormGroup>
                <FormGroup
                  isInline
                  label="Admin Password"
                  fieldId="form-organization"
                >
                  <TextInput
                    type="password"
                    id="form-name"
                    value={adminPassword}
                    onChange={(_, val) => {
                      setAdminPassword(val);
                    }}
                  />
                </FormGroup>
                <Button
                  variant="primary"
                  id=""
                  isLoading={convertAccountLoading}
                  onClick={() => {
                    convert({
                      adminPassword,
                      adminUser,
                    });
                  }}
                >
                  Save
                </Button>
              </Form>
            </>
          )}
        </>
      )}

      <ActionGroup>
        <Flex
          justifyContent={{default: 'justifyContentFlexEnd'}}
          width={'100%'}
          style={{
            display:
              !user.organizations.length && accountType == 'organization'
                ? 'none'
                : 'undefined',
          }}
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

      <UserConvertConflictsModal
        isModalOpen={convertConflictModalOpen}
        items={user.organizations}
        handleModalToggle={() => setConvertConflictModalOpen(false)}
        mapOfColNamesToTableData={{}}
      />
    </Form>
  );
};
