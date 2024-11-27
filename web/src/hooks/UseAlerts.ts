import {useRecoilState} from 'recoil';
import {AlertDetails, alertState} from 'src/atoms/AlertState';

export function useAlerts() {
  const [alerts, setAlerts] = useRecoilState(alertState);
  const addAlert = (alert: AlertDetails) => {
    if (alert.key == null) {
      alert.key = Math.random().toString(36).substring(7);
    }
    setAlerts([...alerts, alert]);
  };

  const clearAllAlerts = () => {
    setAlerts([]);
  };

  return {
    addAlert,
    clearAllAlerts,
  };
}
