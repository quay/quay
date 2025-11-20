import {ReactNode, useEffect, useState} from 'react';
import {FreshLoginModal} from 'src/components/modals/FreshLoginModal';
import {SessionExpiredModal} from 'src/components/modals/SessionExpiredModal';
import {useGlobalFreshLogin} from 'src/hooks/UseGlobalFreshLogin';
import {AlertVariant, useUI} from 'src/contexts/UIContext';

interface AppWithFreshLoginProps {
  children: ReactNode;
}

export function AppWithFreshLogin({children}: AppWithFreshLoginProps) {
  const {isLoading, handleVerify, handleCancel} = useGlobalFreshLogin();
  const [isFreshLoginModalOpen, setIsFreshLoginModalOpen] = useState(false);
  const [isSessionExpiredModalOpen, setIsSessionExpiredModalOpen] =
    useState(false);
  const {addAlert} = useUI();

  useEffect(() => {
    const handleFreshLoginRequired = () => {
      setIsFreshLoginModalOpen(true);
    };

    const handleSessionExpired = () => {
      setIsSessionExpiredModalOpen(true);
    };

    window.addEventListener('freshLoginRequired', handleFreshLoginRequired);
    window.addEventListener('sessionExpired', handleSessionExpired);
    return () => {
      window.removeEventListener(
        'freshLoginRequired',
        handleFreshLoginRequired,
      );
      window.removeEventListener('sessionExpired', handleSessionExpired);
    };
  }, []);

  const handleVerifyWrapper = async (password: string) => {
    try {
      await handleVerify(password);
      setIsFreshLoginModalOpen(false);
    } catch (err) {
      // On verification failure, close modal and show toast alert
      setIsFreshLoginModalOpen(false);
      const errorMessage = (err as Error).message;
      addAlert({
        variant: AlertVariant.Failure,
        title: 'Invalid verification credentials',
        message: errorMessage,
      });
    }
  };

  const handleCancelWrapper = () => {
    handleCancel();
    setIsFreshLoginModalOpen(false);
  };

  const handleSignIn = () => {
    // Clear any stale state and redirect to signin
    setIsSessionExpiredModalOpen(false);
    window.location.href = '/signin';
  };

  return (
    <>
      {children}
      <FreshLoginModal
        isOpen={isFreshLoginModalOpen}
        onVerify={handleVerifyWrapper}
        onCancel={handleCancelWrapper}
        isLoading={isLoading}
      />
      <SessionExpiredModal
        isOpen={isSessionExpiredModalOpen}
        onSignIn={handleSignIn}
      />
    </>
  );
}
