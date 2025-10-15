import React, {useState} from 'react';
import {
  Modal,
  ModalVariant,
  Button,
  Form,
  FormGroup,
  TextInput,
  Alert,
  Radio,
  List,
  ListItem,
  Flex,
  FlexItem,
  Spinner,
  Text,
} from '@patternfly/react-core';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
import {useConvertAccount} from 'src/hooks/UseConvertAccount';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {useAlerts} from 'src/hooks/UseAlerts';
import {AlertVariant} from 'src/atoms/AlertState';
import Avatar from 'src/components/Avatar';

interface ChangeAccountTypeModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function ChangeAccountTypeModal({
  isOpen,
  onClose,
}: ChangeAccountTypeModalProps) {
  const {user} = useCurrentUser();
  const quayConfig = useQuayConfig();
  const {addAlert} = useAlerts();
  const canConvert = user?.organizations?.length === 0;
  const [convertStep, setConvertStep] = useState(canConvert ? 1 : 0); // Start at step 1 if can convert
  const [accountType, setAccountType] = useState('organization'); // Default to organization
  const [adminUsername, setAdminUsername] = useState('');
  const [adminPassword, setAdminPassword] = useState('');
  const [selectedPlan, setSelectedPlan] = useState('');
  const [error, setError] = useState<string>('');
  const orgCount = user?.organizations?.length || 0;

  const convertAccountMutator = useConvertAccount({
    onSuccess: () => {
      addAlert({
        title: 'Account successfully converted to organization',
        variant: AlertVariant.Success,
      });
      handleClose();
      // Redirect to the organization page
      window.location.href = `/organization/${user?.username}`;
    },
    onError: (error) => {
      setError(error?.response?.data?.detail || 'Failed to convert account');
      setConvertStep(canConvert ? 1 : 0); // Go back to appropriate starting step
    },
  });

  const handleClose = () => {
    setConvertStep(canConvert ? 1 : 0);
    setAccountType('organization');
    setAdminUsername('');
    setAdminPassword('');
    setSelectedPlan('');
    setError('');
    onClose();
  };

  const handleShowConvertForm = () => {
    setConvertStep(1);
  };

  const handleNextStep = () => {
    if (convertStep === 1) {
      // Validate admin user form
      if (!adminUsername || !adminPassword) {
        setError('Admin username and password are required');
        return;
      }

      if (quayConfig?.features?.BILLING) {
        setConvertStep(2); // Go to billing step
      } else {
        performConversion(); // Skip billing, go straight to conversion
      }
    } else if (convertStep === 2) {
      if (!selectedPlan) {
        setError('Please select a billing plan');
        return;
      }
      performConversion();
    }
  };

  const performConversion = () => {
    setConvertStep(3); // Show loading step
    setError('');

    const convertRequest = {
      adminUser: adminUsername,
      adminPassword: adminPassword,
      ...(quayConfig?.features?.BILLING &&
        selectedPlan && {plan: selectedPlan}),
    };

    convertAccountMutator.convert(convertRequest);
  };

  // Step 0 - Account type selection or blocking message
  const renderStep0 = () => (
    <>
      {!canConvert ? (
        <div>
          <p>
            This account cannot be converted into an organization, as it is a
            member of {orgCount} other organization{orgCount > 1 ? 's' : ''}.
          </p>
          <br />
          <p>Please leave the following organizations first:</p>
          <List>
            {user?.organizations
              ?.filter((org) => org && org.name)
              ?.map((org) => (
                <ListItem key={org.name}>
                  <Flex alignItems={{default: 'alignItemsCenter'}}>
                    {org.avatar && (
                      <FlexItem spacer={{default: 'spacerSm'}}>
                        <Avatar avatar={org.avatar} size="sm" />
                      </FlexItem>
                    )}
                    <FlexItem>
                      <a href={`/organization/${org.name}`}>{org.name}</a>
                    </FlexItem>
                  </Flex>
                </ListItem>
              ))}
          </List>
        </div>
      ) : (
        <div>
          <FormGroup>
            <Radio
              id="accountTypeI"
              name="accountType"
              label="Individual account (current)"
              description="Single account with multiple repositories"
              isChecked={accountType === 'user'}
              onChange={() => setAccountType('user')}
            />
            <Radio
              id="accountTypeO"
              name="accountType"
              label="Organization"
              description="Multiple users and teams that share access and billing under a single namespace"
              isChecked={accountType === 'organization'}
              onChange={() => setAccountType('organization')}
            />
          </FormGroup>
        </div>
      )}
    </>
  );

  // Step 1 - Admin user setup
  const renderStep1 = () => (
    <div>
      <p>
        Fill out the form below to convert your current user account into an
        organization. Your existing repositories will be maintained under the
        namespace. All <strong>direct</strong> permissions delegated to{' '}
        {user?.username} will be deleted.
      </p>
      <br />

      <Form>
        <FormGroup label="Organization Name" fieldId="org-name">
          <div style={{display: 'flex', alignItems: 'center', gap: '8px'}}>
            <Avatar avatar={user?.avatar} size="sm" />
            <Text>{user?.username}</Text>
          </div>
          <Text
            component="small"
            style={{color: 'var(--pf-v5-global--Color--200)'}}
          >
            This will continue to be the namespace for your repositories
          </Text>
        </FormGroup>

        <FormGroup label="Admin User" fieldId="admin-user">
          <TextInput
            id="admin-username"
            type="text"
            value={adminUsername}
            onChange={(_event, value) => setAdminUsername(value)}
            placeholder="Admin Username"
            isRequired
          />
          <TextInput
            id="admin-password"
            type="password"
            value={adminPassword}
            onChange={(_event, value) => setAdminPassword(value)}
            placeholder="Admin Password"
            isRequired
            style={{marginTop: '8px'}}
          />
          <Text
            component="small"
            style={{color: 'var(--pf-v5-global--Color--200)'}}
          >
            The username and password for the account that will become an
            administrator of the organization. Note that this account{' '}
            <strong>must be a separate registered account</strong> from the
            account that you are trying to convert, and{' '}
            <strong>must already exist</strong>.
          </Text>
        </FormGroup>
      </Form>
    </div>
  );

  // Step 2 - Billing plan selection (simplified)
  const renderStep2 = () => (
    <div>
      <p>
        Please select the billing plan to use for the new organization. Select
        &quot;Open Source&quot; to create an organization without private
        repositories.
      </p>
      <br />

      <FormGroup>
        <Radio
          id="plan-free"
          name="plan"
          label="Open Source"
          description="Free plan for open source projects"
          isChecked={selectedPlan === 'free'}
          onChange={() => setSelectedPlan('free')}
        />
        {/* Additional plans would be rendered here based on available plans */}
      </FormGroup>
    </div>
  );

  // Step 3 - Loading/conversion
  const renderStep3 = () => (
    <div style={{textAlign: 'center', padding: '2rem'}}>
      <Spinner size="lg" />
      <br />
      <p>Converting your account...</p>
    </div>
  );

  const getStepActions = () => {
    if (convertStep === 0) {
      if (!canConvert) {
        return [
          <Button
            key="close"
            variant="primary"
            data-testid="change-account-type-modal-close"
            onClick={handleClose}
          >
            Close
          </Button>,
        ];
      } else {
        return [
          <Button
            key="close"
            variant="secondary"
            onClick={handleClose}
            isDisabled={accountType !== 'user'}
          >
            Close
          </Button>,
          <Button
            key="convert"
            variant="primary"
            onClick={handleShowConvertForm}
            isDisabled={accountType !== 'organization'}
          >
            Convert Account
          </Button>,
        ];
      }
    } else if (convertStep === 1) {
      return [
        <Button key="cancel" variant="secondary" onClick={handleClose}>
          Cancel
        </Button>,
        <Button
          key="next"
          variant="primary"
          onClick={handleNextStep}
          isDisabled={!adminUsername || !adminPassword}
          data-testid="account-type-next"
        >
          {quayConfig?.features?.BILLING ? 'Choose billing' : 'Convert Account'}
        </Button>,
      ];
    } else if (convertStep === 2) {
      return [
        <Button key="cancel" variant="secondary" onClick={handleClose}>
          Cancel
        </Button>,
        <Button
          key="convert"
          variant="primary"
          onClick={handleNextStep}
          isDisabled={!selectedPlan}
          data-testid="account-type-convert"
        >
          Convert Account
        </Button>,
      ];
    } else {
      return []; // No actions during conversion
    }
  };

  const renderCurrentStep = () => {
    switch (convertStep) {
      case 0:
        return renderStep0();
      case 1:
        return renderStep1();
      case 2:
        return renderStep2();
      case 3:
        return renderStep3();
      default:
        return renderStep0();
    }
  };

  return (
    <Modal
      variant={ModalVariant.medium}
      title="Change Account Type"
      isOpen={isOpen}
      onClose={handleClose}
      data-testid="change-account-type-modal"
      actions={convertStep < 3 ? getStepActions() : []}
    >
      {error && (
        <Alert
          variant="danger"
          isInline
          title="Error"
          className="pf-v5-u-mb-md"
        >
          {error}
        </Alert>
      )}

      {renderCurrentStep()}
    </Modal>
  );
}
