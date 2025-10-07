import {useQuayConfig} from './UseQuayConfig';

export function useQuayState() {
  const config = useQuayConfig();

  const inReadOnlyMode = config?.registry_state === 'readonly';
  const inAccountRecoveryMode = config?.account_recovery_mode === true;

  return {
    inReadOnlyMode,
    inAccountRecoveryMode,
  };
}
