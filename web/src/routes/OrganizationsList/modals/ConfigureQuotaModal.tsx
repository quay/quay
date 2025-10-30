import {Modal, ModalVariant} from '@patternfly/react-core';
import {QuotaManagement} from 'src/routes/OrganizationsList/Organization/Tabs/Settings/QuotaManagement';

interface ConfigureQuotaModalProps {
  isOpen: boolean;
  onClose: () => void;
  organizationName: string;
  isUser: boolean;
}

export function ConfigureQuotaModal(props: ConfigureQuotaModalProps) {
  return (
    <Modal
      variant={ModalVariant.large}
      title={`Configure Quota for ${props.organizationName}`}
      isOpen={props.isOpen}
      onClose={props.onClose}
      data-testid="configure-quota-modal"
    >
      <QuotaManagement
        organizationName={props.organizationName}
        isUser={props.isUser}
        view="super-user"
      />
    </Modal>
  );
}
