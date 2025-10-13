import React, {useState} from 'react';
import {
  Button,
  ClipboardCopy,
  DescriptionList,
  DescriptionListTerm,
  DescriptionListGroup,
  DescriptionListDescription,
  PageSection,
  Stack,
  StackItem,
  Content,
} from '@patternfly/react-core';
import {
  IOAuthApplication,
  useResetOAuthApplicationClientSecret,
} from 'src/hooks/UseOAuthApplications';
import {useAlerts} from 'src/hooks/UseAlerts';
import {AlertVariant} from 'src/atoms/AlertState';
import {ConfirmationModal} from 'src/components/modals/ConfirmationModal';

interface OAuthInformationTabProps {
  application: IOAuthApplication | null;
  orgName: string;
  onSuccess: () => void;
  updateSelectedApplication: (updatedApplication: IOAuthApplication) => void;
}

export default function OAuthInformationTab(props: OAuthInformationTabProps) {
  const [isResetModalOpen, setIsResetModalOpen] = useState(false);
  const {addAlert} = useAlerts();

  const {resetOAuthApplicationClientSecretMutation} =
    useResetOAuthApplicationClientSecret(
      props.orgName,
      (updatedApplication: IOAuthApplication) => {
        // onSuccess callback - update the displayed application data
        addAlert({
          variant: AlertVariant.Success,
          title: 'Client secret reset successfully',
        });
        props.updateSelectedApplication(updatedApplication);
        props.onSuccess();
      },
      () => {
        // onError callback
        addAlert({
          variant: AlertVariant.Failure,
          title: 'Failed to reset client secret',
        });
      },
    );

  if (!props.application) {
    return <Content component="p">No application selected</Content>;
  }

  const handleResetSecret = () => {
    if (props.application?.client_id) {
      resetOAuthApplicationClientSecretMutation(props.application.client_id);
      setIsResetModalOpen(false);
    }
  };

  const toggleResetModal = () => {
    setIsResetModalOpen(!isResetModalOpen);
  };

  return (
    <PageSection hasBodyWrapper={false}>
      <Stack hasGutter>
        <StackItem>
          <DescriptionList isHorizontal>
            <DescriptionListGroup>
              <DescriptionListTerm>Client ID:</DescriptionListTerm>
              <DescriptionListDescription>
                <ClipboardCopy
                  hoverTip="Copy"
                  clickTip="Copied"
                  variant="inline-compact"
                  data-testid="client-id-copy"
                >
                  {props.application.client_id}
                </ClipboardCopy>
              </DescriptionListDescription>
            </DescriptionListGroup>

            <DescriptionListGroup>
              <DescriptionListTerm>Client Secret:</DescriptionListTerm>
              <DescriptionListDescription>
                <Content component="p">
                  {props.application.client_secret}
                </Content>
              </DescriptionListDescription>
            </DescriptionListGroup>
          </DescriptionList>
        </StackItem>

        <StackItem>
          <Button
            variant="primary"
            onClick={toggleResetModal}
            data-testid="reset-client-secret-button"
          >
            Reset Client Secret
          </Button>
        </StackItem>
      </Stack>

      <ConfirmationModal
        title="Reset Client Secret?"
        description="Are you sure you want to reset your Client Secret? Any existing users of this Secret will break!"
        buttonText="Reset"
        modalOpen={isResetModalOpen}
        toggleModal={toggleResetModal}
        handleModalConfirm={handleResetSecret}
        confirmButtonTestId="confirm-reset-secret"
      />
    </PageSection>
  );
}
