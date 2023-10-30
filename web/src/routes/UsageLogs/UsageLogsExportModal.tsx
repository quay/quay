import React from 'react';
import {
  Button,
  Text,
  Modal,
  ModalVariant,
  TextInput,
  HelperText,
  HelperTextItem,
  Alert,
  AlertGroup,
} from '@patternfly/react-core';

import {
  exportLogsForOrg,
  exportLogsForRepository,
} from 'src/hooks/UseExportLogs';

export default function ExportLogsModal(props: ExportLogsModalProps) {
  const [isModalOpen, setIsModalOpen] = React.useState(false);
  const [callbackEmailOrUrl, setCallbackEmailOrUrl] = React.useState('');
  const handleModalToggle = (_event: KeyboardEvent | React.MouseEvent) => {
    setIsModalOpen(!isModalOpen);
  };
  const timeout = 8000;
  const [alerts, setAlerts] = React.useState<React.ReactNode[]>([]);

  const exportLogs = (callback: string) => {
    switch (props.type) {
      case 'repository':
        return exportLogsForRepository(
          props.organization,
          props.repository,
          props.starttime,
          props.endtime,
          callback,
        );
      case 'org':
        return exportLogsForOrg(
          props.organization,
          props.starttime,
          props.endtime,
          callback,
        );
      default:
        break;
    }
  };

  return (
    <React.Fragment>
      <Button variant="primary" onClick={handleModalToggle}>
        Export
      </Button>
      <Modal
        variant={ModalVariant.medium}
        title="Export Usage Logs"
        isOpen={isModalOpen}
        onClose={handleModalToggle}
        actions={[
          <Button
            key="confirm"
            variant="primary"
            onClick={() =>
              exportLogs(callbackEmailOrUrl).then((response) => {
                if (response['export_id']) {
                  setAlerts(() => {
                    return [
                      <Alert
                        key={response['export_id']}
                        variant="success"
                        title="Success"
                        id="export-logs-success"
                        timeout={timeout}
                      >
                        exported with id {response['export_id']}
                      </Alert>,
                    ];
                  });
                } else {
                  setAlerts(() => {
                    return [
                      <Alert
                        key={response['error_type']}
                        variant="danger"
                        title="Error"
                        id="export-logs-error"
                        timeout={timeout}
                      >
                        problem exporting logs: {response['error_message']}
                      </Alert>,
                    ];
                  });
                }
              })
            }
          >
            {' '}
            Confirm
          </Button>,
          <Button key="cancel" variant="link" onClick={handleModalToggle}>
            Cancel
          </Button>,
        ]}
      >
        <Text>
          Enter an e-mail address or callback URL (must start with http:// or
          https://) at which to receive the exported logs once they have been
          fully processed:
        </Text>
        <TextInput
          id="export-logs-callback"
          value={callbackEmailOrUrl}
          type="text"
          onChange={(_event, callbackEmailOrUrl) =>
            setCallbackEmailOrUrl(callbackEmailOrUrl)
          }
        ></TextInput>
        <HelperText>
          <HelperTextItem variant="indeterminate">
            {' '}
            Note: The export process can take up to an hour to process if there
            are many logs. As well, only a single export process can run at a
            time for each namespace. Additional export requests will be queued.{' '}
          </HelperTextItem>
        </HelperText>
        <AlertGroup isToast isLiveRegion>
          {alerts}
        </AlertGroup>
      </Modal>
    </React.Fragment>
  );
}

interface ExportLogsModalProps {
  organization: string;
  repository: string;
  starttime: string;
  endtime: string;
  type: string;
}
