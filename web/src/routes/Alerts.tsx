import {
  Alert,
  AlertActionCloseButton,
  AlertGroup,
} from '@patternfly/react-core';
import {useUI, AlertVariant} from 'src/contexts/UIContext';

export default function Alerts() {
  const {alerts, removeAlert} = useUI();
  return (
    <AlertGroup isToast isLiveRegion>
      {alerts.map((alert) => (
        <Alert
          isExpandable={alert.message != null}
          variant={alert.variant}
          title={alert.title}
          timeout={alert.variant === AlertVariant.Success}
          actionClose={
            <AlertActionCloseButton
              onClose={() => {
                removeAlert(alert.key);
              }}
            />
          }
          key={alert.key}
        >
          {alert.message}
        </Alert>
      ))}
    </AlertGroup>
  );
}
