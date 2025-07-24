import React, {useState} from 'react';
import {
  Alert,
  Button,
  ClipboardCopy,
  DescriptionList,
  DescriptionListTerm,
  DescriptionListGroup,
  DescriptionListDescription,
  Flex,
  FlexItem,
  PageSection,
  PageSectionVariants,
  Title,
} from '@patternfly/react-core';
import {EyeIcon, EyeSlashIcon} from '@patternfly/react-icons';
import {
  IOAuthApplication,
  useResetOAuthApplicationClientSecret,
} from 'src/hooks/UseOAuthApplications';
import {useAlerts} from 'src/hooks/UseAlerts';
import {AlertVariant} from 'src/atoms/AlertState';

interface OAuthInformationTabProps {
  application: IOAuthApplication | null;
  orgName: string;
  onSuccess: () => void;
}

export default function OAuthInformationTab(props: OAuthInformationTabProps) {
  const [showSecret, setShowSecret] = useState(false);
  const {addAlert} = useAlerts();

  const {
    resetOAuthApplicationClientSecretMutation,
    errorResetOAuthApplicationClientSecret,
    successResetOAuthApplicationClientSecret,
  } = useResetOAuthApplicationClientSecret(props.orgName);

  if (!props.application) {
    return <div>No application selected</div>;
  }

  const handleResetSecret = () => {
    if (props.application?.client_id) {
      resetOAuthApplicationClientSecretMutation(props.application.client_id);
    }
  };

  // Show success/error alerts
  React.useEffect(() => {
    if (successResetOAuthApplicationClientSecret) {
      addAlert({
        variant: AlertVariant.Success,
        title: 'Client secret reset successfully',
      });
    }
  }, [successResetOAuthApplicationClientSecret]);

  React.useEffect(() => {
    if (errorResetOAuthApplicationClientSecret) {
      addAlert({
        variant: AlertVariant.Failure,
        title: 'Failed to reset client secret',
      });
    }
  }, [errorResetOAuthApplicationClientSecret]);

  const maskedSecret = props.application.client_secret
    ? '•'.repeat(props.application.client_secret.length)
    : 'No secret available';

  return (
    <PageSection variant={PageSectionVariants.light}>
      <Title headingLevel="h3" size="lg">
        OAuth Application Credentials
      </Title>

      <DescriptionList isHorizontal>
        <DescriptionListGroup>
          <DescriptionListTerm>Application Name</DescriptionListTerm>
          <DescriptionListDescription>
            {props.application.name}
          </DescriptionListDescription>
        </DescriptionListGroup>

        <DescriptionListGroup>
          <DescriptionListTerm>Client ID</DescriptionListTerm>
          <DescriptionListDescription>
            <ClipboardCopy
              hoverTip="Copy"
              clickTip="Copied"
              variant="inline-compact"
            >
              {props.application.client_id}
            </ClipboardCopy>
          </DescriptionListDescription>
        </DescriptionListGroup>

        <DescriptionListGroup>
          <DescriptionListTerm>Client Secret</DescriptionListTerm>
          <DescriptionListDescription>
            <Flex alignItems={{default: 'alignItemsCenter'}}>
              <FlexItem>
                <ClipboardCopy
                  hoverTip="Copy"
                  clickTip="Copied"
                  variant="inline-compact"
                  isReadOnly={!showSecret}
                >
                  {showSecret ? props.application.client_secret : maskedSecret}
                </ClipboardCopy>
              </FlexItem>
              <FlexItem>
                <Button
                  variant="link"
                  icon={showSecret ? <EyeSlashIcon /> : <EyeIcon />}
                  onClick={() => setShowSecret(!showSecret)}
                  aria-label={showSecret ? 'Hide secret' : 'Show secret'}
                >
                  {showSecret ? 'Hide' : 'Show'}
                </Button>
              </FlexItem>
            </Flex>
          </DescriptionListDescription>
        </DescriptionListGroup>
      </DescriptionList>

      <Alert
        variant="warning"
        title="Keep your client secret secure"
        style={{marginTop: '1rem', marginBottom: '1rem'}}
      >
        Your client secret is used to authenticate your application. Keep it
        confidential and secure. If compromised, reset it immediately.
      </Alert>

      <Button
        variant="danger"
        onClick={handleResetSecret}
        style={{marginTop: '1rem'}}
      >
        Reset Client Secret
      </Button>
    </PageSection>
  );
}
