import {useRef, useState} from 'react';
import {Link, Navigate, useLocation, useNavigate} from 'react-router-dom';
import {
  Alert,
  Breadcrumb,
  BreadcrumbItem,
  Button,
  Content,
  Form,
  FormGroup,
  FormHelperText,
  HelperText,
  HelperTextItem,
  Radio,
  Skeleton,
  Stack,
  TextInput,
  Title,
} from '@patternfly/react-core';
import {Table, Tbody, Td, Th, Thead, Tr} from '@patternfly/react-table';
import ExclamationCircleIcon from '@patternfly/react-icons/dist/esm/icons/exclamation-circle-icon';
import {useCreateOrganization} from 'src/hooks/UseCreateOrganization';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {isValidEmail} from 'src/libs/utils';
import {
  formatPlanPrice,
  getBillingErrorMessage,
  getOrganizationCreationPlans,
  getPlanInformationPath,
} from 'src/libs/billing';
import {NavigationPath} from 'src/routes/NavigationPath';

const nameHelp =
  'This will also be the namespace for your repositories. Must be alphanumeric, all lowercase, at least 2 characters long and at most 255 characters long';

const CreateOrganization: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const {user} = useCurrentUser();
  const config = useQuayConfig();
  const billingEnabled = config?.features?.BILLING === true;
  const {plans, creation, checkout} = useCreateOrganization(
    billingEnabled && !!user && !user.anonymous,
  );
  const [organizationName, setOrganizationName] = useState('');
  const [contactEmail, setContactEmail] = useState('');
  const [emailTouched, setEmailTouched] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const submitting = useRef(false);
  const availablePlans = getOrganizationCreationPlans(plans.data ?? []);
  const plan = availablePlans.find((entry) => entry.stripeId === selectedPlan);
  const createdName = creation.data?.name;
  const validName =
    /^([a-z0-9]+(?:[._-][a-z0-9]+)*)$/.test(organizationName) &&
    organizationName.length >= 2 &&
    organizationName.length <= 255;
  const validEmail = !contactEmail || isValidEmail(contactEmail);
  const nameWarning =
    validName && (organizationName.length > 30 || organizationName.length < 4)
      ? 'Namespaces less than 4 or more than 30 characters are only compatible with Docker 1.6+'
      : validName &&
          (organizationName.includes('.') || organizationName.includes('-'))
        ? 'Namespaces with dashes or dots are only compatible with Docker 1.9+'
        : null;
  const nameVariant =
    organizationName && !validName
      ? 'error'
      : nameWarning
        ? 'warning'
        : 'default';
  const canSubmit =
    validName &&
    validEmail &&
    (!billingEnabled || (!!plan && !plans.isError && !plans.isFetching));

  const submit = async () => {
    if (submitting.current || !canSubmit) return;
    submitting.current = true;
    setBusy(true);
    setError(null);
    try {
      const name =
        createdName ??
        (
          await creation.mutateAsync({
            name: organizationName,
            email: contactEmail || undefined,
          })
        ).name;
      if (!billingEnabled || plan.price === 0) {
        navigate(`/organization/${encodeURIComponent(name)}`, {
          state: {createdOrganization: name},
        });
        return;
      }
      // Reuse an already returned session if browser navigation failed.
      const session =
        checkout.data ??
        (await checkout.mutateAsync({name, plan: plan.stripeId}));
      if (session) window.location.assign(session.url);
      else navigate(getPlanInformationPath(name));
    } catch (error) {
      setError(error);
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  };

  if (user?.anonymous) {
    return (
      <Navigate
        to={`/signin?redirect_url=${encodeURIComponent(
          location.pathname + location.search,
        )}`}
        replace
      />
    );
  }

  return (
    <Stack hasGutter data-testid="create-organization-page">
      <Breadcrumb aria-label="Organization creation navigation">
        <BreadcrumbItem>
          <Link to={NavigationPath.organizationsList}>Organizations</Link>
        </BreadcrumbItem>
        <BreadcrumbItem isActive>Create organization</BreadcrumbItem>
      </Breadcrumb>
      <Title headingLevel="h1">Create Organization</Title>
      <Content>
        Create a shared namespace for your repositories, teams, and permissions.
      </Content>
      {error != null && (
        <Alert
          isInline
          isLiveRegion
          data-testid="create-organization-error"
          variant="danger"
          title={
            createdName
              ? 'Organization created; payment setup could not be started'
              : 'Unable to create organization'
          }
        >
          {createdName && (
            <p>
              {createdName} is available. Retry checkout or go to your
              organization.
            </p>
          )}
          {getBillingErrorMessage(error)}
        </Alert>
      )}
      <Form
        id="create-organization-form"
        onSubmit={(event) => {
          event.preventDefault();
          void submit();
        }}
      >
        <FormGroup
          label="Organization Name"
          isRequired
          fieldId="create-org-name-input"
        >
          <TextInput
            isRequired
            id="create-org-name-input"
            aria-describedby="create-org-name-help"
            value={organizationName}
            onChange={(_event, value) => setOrganizationName(value)}
            validated={nameVariant}
            isDisabled={busy || !!createdName}
            style={{maxWidth: '480px'}}
          />
          <FormHelperText>
            <HelperText id="create-org-name-help" isLiveRegion>
              <HelperTextItem
                variant={nameVariant}
                {...(nameVariant === 'error' && {
                  icon: <ExclamationCircleIcon />,
                })}
              >
                {nameVariant === 'error'
                  ? 'Must be alphanumeric, all lowercase, at least 2 characters long and at most 255 characters long'
                  : nameWarning || nameHelp}
              </HelperTextItem>
            </HelperText>
          </FormHelperText>
        </FormGroup>
        <FormGroup label="Email (Optional)" fieldId="create-org-email-input">
          <TextInput
            type="email"
            id="create-org-email-input"
            aria-describedby="create-org-email-help"
            value={contactEmail}
            onChange={(_event, value) => setContactEmail(value)}
            onBlur={() => setEmailTouched(true)}
            validated={emailTouched && !validEmail ? 'error' : 'default'}
            isDisabled={busy || !!createdName}
            style={{maxWidth: '480px'}}
          />
          <FormHelperText>
            <HelperText id="create-org-email-help" isLiveRegion>
              <HelperTextItem
                variant={emailTouched && !validEmail ? 'error' : 'default'}
              >
                {emailTouched && !validEmail
                  ? 'Enter a valid email: email@provider.com'
                  : 'Optional. Used for organization recovery and notifications.'}
              </HelperTextItem>
            </HelperText>
          </FormHelperText>
        </FormGroup>
        {billingEnabled && (
          <FormGroup
            label="Choose your organization's plan"
            isRequired
            fieldId="organization-plan-selection"
            role="radiogroup"
            aria-required="true"
          >
            {plans.isLoading ? (
              <Skeleton
                height="240px"
                screenreaderText="Loading organization plans"
              />
            ) : plans.isError ? (
              <Alert
                isInline
                isLiveRegion
                variant="danger"
                title="Unable to load organization plans"
              >
                <Button
                  variant="link"
                  isInline
                  onClick={() => void plans.refetch()}
                >
                  Retry loading plans
                </Button>
              </Alert>
            ) : availablePlans.length === 0 ? (
              <Alert
                isInline
                variant="warning"
                title="No organization plans are available"
              />
            ) : (
              <Table
                id="organization-plan-selection"
                aria-label="Organization plans"
              >
                <Thead>
                  <Tr>
                    <Th>Plan</Th>
                    <Th modifier="wrap">Private repositories</Th>
                    <Th>Price</Th>
                    <Th>Select plan</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {availablePlans.map((entry) => (
                    <Tr
                      key={entry.stripeId}
                      isRowSelected={selectedPlan === entry.stripeId}
                    >
                      <Td dataLabel="Plan">{entry.title}</Td>
                      <Td dataLabel="Private repositories">
                        {entry.privateRepos}
                      </Td>
                      <Td dataLabel="Price">{formatPlanPrice(entry.price)}</Td>
                      <Td dataLabel="Select plan">
                        <Radio
                          id={`organization-plan-${entry.stripeId}`}
                          name="organization-plan"
                          label={`Choose ${entry.title}`}
                          isChecked={selectedPlan === entry.stripeId}
                          onChange={() => setSelectedPlan(entry.stripeId)}
                          isDisabled={busy || !!createdName}
                        />
                      </Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            )}
          </FormGroup>
        )}
        {plan && plan.price > 0 && (
          <Content>
            Your organization will be created before you continue to Stripe to
            set up payment.
          </Content>
        )}
        <div>
          <Button
            id="create-org-confirm"
            type="submit"
            isLoading={busy}
            isDisabled={busy || !canSubmit}
          >
            {createdName
              ? 'Retry checkout'
              : plan && plan.price > 0
                ? 'Create and continue to checkout'
                : 'Create organization'}
          </Button>{' '}
          <Button
            id="create-org-cancel"
            variant="link"
            isDisabled={busy}
            onClick={() =>
              navigate(
                createdName
                  ? `/organization/${encodeURIComponent(createdName)}`
                  : NavigationPath.organizationsList,
              )
            }
          >
            {createdName ? 'Go to organization' : 'Cancel'}
          </Button>
        </div>
      </Form>
    </Stack>
  );
};

export default CreateOrganization;
