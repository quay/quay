import {IRobot} from 'src/resources/RobotsResource';
import {
  ActionGroup,
  Button,
  Flex,
  FlexItem,
  Form,
  FormFieldGroupExpandable,
  FormFieldGroupHeader,
  FormGroup,
  Spinner,
  TextInput,
} from '@patternfly/react-core';
import {PlusIcon, TrashIcon} from '@patternfly/react-icons';
import React, {useEffect, useState} from 'react';
import DisplayModal from './robotAccountWizard/DisplayModal';
import {useRobotFederation} from 'src/hooks/useRobotFederation';
import {useAlerts} from 'src/hooks/UseAlerts';
import {AlertVariant} from 'src/atoms/AlertState';

function RobotFederationForm(props: RobotFederationFormProps) {
  const [federationFormState, setFederationFormState] = useState<
    RobotFederationFormEntryProps[]
  >([]);

  const alerts = useAlerts();

  const {robotFederationConfig, loading, fetchError, setRobotFederationConfig} =
    useRobotFederation({
      namespace: props.namespace,
      robotName: props.robotAccount.name,
      onSuccess: (result) => {
        setFederationFormState(
          result.map((config) => ({...config, isExpanded: false})),
        );
        alerts.addAlert({
          title: 'Robot federation config saved',
          variant: AlertVariant.Success,
        });
      },
      onError: (e) => {
        alerts.addAlert({
          title: e.error_message || 'Error saving federation config',
          variant: AlertVariant.Failure,
        });
      },
    });

  useEffect(() => {
    if (robotFederationConfig) {
      setFederationFormState(
        robotFederationConfig.map((config) => ({...config, isExpanded: false})),
      );
    }
  }, [robotFederationConfig]);

  if (loading) {
    return <Spinner size="md" />;
  }

  if (fetchError) {
    return <div>Error fetching federation config</div>;
  }

  const addFederationConfigEntry = () => {
    setFederationFormState((prev) => {
      return [
        ...prev,
        {
          issuer: '',
          subject: '',
          isExpanded: true,
        },
      ];
    });
  };

  const updateFederationConfigEntry = (
    index: number,
    issuer: string,
    subject: string,
  ) => {
    setFederationFormState((prev) => {
      return prev.map((config, i) => {
        if (i === index) {
          return {
            issuer,
            subject,
            isExpanded: config.isExpanded,
          };
        }
        return config;
      });
    });
  };

  const removeFederationConfigEntry = (index: number) => {
    setFederationFormState((prev) => {
      return prev.filter((_, i) => i !== index);
    });
  };

  const onFormSave = () => {
    setRobotFederationConfig({
      namespace: props.namespace,
      robotName: props.robotAccount.name,
      config: federationFormState,
    });
  };

  const onFormClose = () => {
    props.onClose();
  };

  return (
    <>
      <Form>
        {federationFormState.map((config, index) => {
          return (
            <RobotFederationFormEntry
              issuer={config.issuer}
              subject={config.subject}
              index={index}
              key={index}
              isExpanded={config.isExpanded}
              onRemove={removeFederationConfigEntry}
              onUpdate={updateFederationConfigEntry}
            />
          );
        })}

        <FormGroup>
          <Flex>
            {federationFormState.length == 0 && (
              <FlexItem>
                <div> No federation configured, add using the plus button </div>
              </FlexItem>
            )}
            <FlexItem align={{default: 'alignRight'}}>
              <Button
                onClick={() => {
                  addFederationConfigEntry();
                }}
              >
                <PlusIcon />
              </Button>
            </FlexItem>
          </Flex>
        </FormGroup>
        <ActionGroup>
          <Button variant="primary" onClick={onFormSave}>
            Save
          </Button>
          <Button variant="link" onClick={onFormClose}>
            Close
          </Button>
        </ActionGroup>
      </Form>
    </>
  );
}

function RobotFederationFormEntry(props: RobotFederationFormEntryProps) {
  return (
    <FormFieldGroupExpandable
      isExpanded={props.isExpanded}
      header={
        <FormFieldGroupHeader
          titleText={{
            text: `${props.issuer} : ${props.subject}`,
            id: `${props.index}-issuer-url`,
          }}
          actions={
            <Button
              onClick={() => {
                props.onRemove(props.index);
              }}
              variant="danger"
            >
              <TrashIcon />
            </Button>
          }
        />
      }
    >
      <FormGroup label={'Issuer URL'} isRequired>
        <TextInput
          value={props.issuer}
          type="text"
          isRequired
          onChange={(event, value) => {
            props.onUpdate(props.index, value, props.subject);
          }}
        />
      </FormGroup>
      <FormGroup label={'Subject'} isRequired>
        <TextInput
          value={props.subject}
          type="text"
          isRequired
          onChange={(event, value) => {
            props.onUpdate(props.index, props.issuer, value);
          }}
        />
      </FormGroup>
    </FormFieldGroupExpandable>
  );
}

export function RobotFederationModal(props: RobotFederationModalProps) {
  return (
    <DisplayModal
      isModalOpen={props.isModalOpen}
      setIsModalOpen={props.setIsModalOpen}
      title={`Robot identity federation configuration for ${props.robotAccount.name}`}
      Component={
        <RobotFederationForm
          robotAccount={props.robotAccount}
          namespace={props.namespace}
          onClose={() => {
            props.setIsModalOpen(false);
          }}
          onSave={() => {
            props.setIsModalOpen(false);
          }}
        />
      }
      showSave={false}
      showFooter={false}
    />
  );
}

interface RobotFederationModalProps {
  robotAccount: IRobot;
  namespace: string;
  isModalOpen: boolean;
  setIsModalOpen: (modalState: boolean) => void;
}

interface RobotFederationFormProps {
  robotAccount: IRobot;
  namespace: string;
  onClose: () => void;
  onSave: () => void;
}

interface RobotFederationFormEntryProps {
  issuer: string;
  subject: string;
  index?: number;
  isExpanded?: boolean;
  onRemove?: (index: number) => void;
  onUpdate?: (index: number, issuer: string, subject: string) => void;
}
