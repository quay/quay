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

import {exportLogs} from 'src/hooks/UseExportLogs';
import {useAlerts} from 'src/hooks/UseAlerts';
import {AlertVariant} from 'src/atoms/AlertState';

export default function ExportLogsModal(props: ExportLogsModalProps) {
  const [isModalOpen, setIsModalOpen] = React.useState(false);
  const [callbackEmailOrUrl, setCallbackEmailOrUrl] = React.useState('');
  const handleModalToggle = (_event: KeyboardEvent | React.MouseEvent) => {
    setIsModalOpen(!isModalOpen);
  };
  const {addAlert} = useAlerts();

  const exportLogsClick = (callback: string) => {
    return exportLogs(
      props.organization,
      props.repository,
      props.starttime,
      props.endtime,
      callback,
    );
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
              exportLogsClick(callbackEmailOrUrl).then((response) => {
                if (response['export_id']) {
                  addAlert({
                    variant: AlertVariant.Success,
                    title: `Logs exported with id ${response['export_id']}`,
                  });
                  setIsModalOpen(false);
                } else {
                  addAlert({
                    variant: AlertVariant.Failure,
                    title: `Problem exporting logs: ${response['error_message']}`,
                  });
                  setIsModalOpen(false);
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
