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
  Radio,
  FormGroup,
  AlertActionLink,
  HelperText,
} from '@patternfly/react-core';
import {useLocation} from 'react-router-dom';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
import {useOrganization} from 'src/hooks/UseOrganization';
import {useUpdateOrganization} from 'src/hooks/UseUpdateOrganization';

import {usePlan} from 'src/hooks/UsePlan';
import {ExclamationCircleIcon} from '@patternfly/react-icons';
import {AxiosError} from 'axios';
import {useUpdateUser} from 'src/hooks/UseUpdateUser';
import {UserConvertConflictsModal} from 'src/components/modals/UserConvertConflictsModal';
import {useConvertAccount} from 'src/hooks/UseConvertAccount';

export const BillingInformation = () => {
  const location = useLocation();
  const organizationName = location.pathname.split('/')[2];
  const {plan} = usePlan(organizationName);
  const {user} = useCurrentUser();

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

  const [accountType, setAccountType] = useState(
    isUserOrganization ? 'individual' : 'organization',
  );
  useEffect(() => {
    setAccountType(isUserOrganization ? 'individual' : 'organization');
  }, [loading]);

  const {
    updateOrganization,
    loading: organizationUpdateLoading,
    error: organizationUpdateError,
  } = useUpdateOrganization({
    onSuccess: () => {
      setTouched(false);
    },
    onError: (err) => {
      console.log(err);
    },
  });

  const {
    updateUser,
    loading: userUpdateLoading,
    error: userUpdateError,
  } = useUpdateUser({
    onSuccess: () => {
      setTouched(false);
    },
    onError: (err) => {
      console.log(err);
    },
  });

  const {
    convert,
    loading: convertAccountLoading,
    error: convertAccountError,
  } = useConvertAccount({
    onSuccess: () => {
      setTouched(false);
    },
    onError: (err) => {
      console.log(err);
    },
  });

  const error =
    userUpdateError || organizationUpdateError || convertAccountError;

  const updateLoading = userUpdateLoading || organizationUpdateLoading;
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
            {plan?.plan.toUpperCase()} organization&apos;s plan
          </Title>
        </FlexItem>
        <FlexItem>{`100 of 125 private repositories used`}</FlexItem>
        <FlexItem>{`20 of unlimited public repositories used`}</FlexItem>
      </Flex>

      <Flex width={'70%'}>
        <Button variant="secondary">Change Plan</Button>
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
      <FormGroup
        isInline
        label="Invoice Email"
        fieldId="form-email"
        validated={validated}
        helperTextInvalid="Must be an email"
        helperTextInvalidIcon={<ExclamationCircleIcon />}
        helperText="Invoices will be sent to this e-mail address."
      >
        <TextInput
          type="email"
          id="modal-with-form-form-name"
          isDisabled={false}
          validated={validated}
          value={invoiceEmailAddress}
          onChange={(val) => {
            setTouched(true);
            setInvoiceEmailAddress(val);
            if (/^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i.test(val)) {
              setValidated('success');
            } else {
              setValidated('error');
            }
          }}
        />
      </FormGroup>
      <Button variant="link" isInline>
        View Invoices
      </Button>

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
                  helperText={'The admin username'}
                >
                  <TextInput
                    type="text"
                    id="form-name"
                    onChange={(val) => {
                      setAdminUser(val);
                    }}
                    value={adminUser}
                  />
                </FormGroup>
                <FormGroup
                  isInline
                  label="Admin Username"
                  fieldId="form-organization"
                  helperText={'The admin username'}
                >
                  <TextInput
                    type="text"
                    id="form-name"
                    value={adminPassword}
                    onChange={(val) => {
                      setAdminPassword(val);
                    }}
                  />
                </FormGroup>
                <Button
                  variant="primary"
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
            isLoading={updateLoading}
            isDisabled={!touched || validated == 'error'}
            onClick={() => {
              if (!isUserOrganization) {
                updateOrganization(organizationName, {
                  invoice_email: invoiceEmail,
                  invoice_email_address: invoiceEmailAddress,
                });
              } else {
                updateUser(organizationName, {
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
      <UserConvertConflictsModal
        isModalOpen={convertConflictModalOpen}
        items={user.organizations}
        handleModalToggle={() => setConvertConflictModalOpen(false)}
        mapOfColNamesToTableData={{}}
      />
    </Form>
  );
};
