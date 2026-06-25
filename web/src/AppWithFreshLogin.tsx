import {ReactNode, useEffect, useState} from 'react';
import {FreshLoginModal} from 'src/components/modals/FreshLoginModal';
import {useGlobalFreshLogin} from 'src/hooks/UseGlobalFreshLogin';
import {AlertVariant, useUI} from 'src/contexts/UIContext';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';

interface AppWithFreshLoginProps {
  children: ReactNode;
}

export function AppWithFreshLogin({children}: AppWithFreshLoginProps) {
  const {isLoading, handleVerify, handleCancel} = useGlobalFreshLogin();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const {addAlert} = useUI();
  const quayConfig = useQuayConfig();

  useEffect(() => {
    const handleFreshLoginRequired = () => {
      // For OIDC authentication, redirect to signin page which will handle OIDC re-authentication
      if (quayConfig?.config?.AUTHENTICATION_TYPE === 'OIDC') {
        // OIDC users don't have passwords in Quay, redirect to OIDC provider for re-authentication
        const currentUrl = encodeURIComponent(window.location.href);
        window.location.href = `/signin?redirect_url=${currentUrl}`;
      } else {
        // For Database and other auth types, show password verification modal
        setIsModalOpen(true);
      }
    };

    window.addEventListener('freshLoginRequired', handleFreshLoginRequired);
    return () => {
      window.removeEventListener(
        'freshLoginRequired',
        handleFreshLoginRequired,
      );
    };
  }, [quayConfig]);

  const handleVerifyWrapper = async (password: string) => {
    try {
      await handleVerify(password);
      setIsModalOpen(false);
    } catch (err) {
      // On verification failure, close modal and show toast alert
      setIsModalOpen(false);
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
    setIsModalOpen(false);
  };

  return (
    <>
      {children}
      <FreshLoginModal
        isOpen={isModalOpen}
        onVerify={handleVerifyWrapper}
        onCancel={handleCancelWrapper}
        isLoading={isLoading}
      />
    </>
  );
}
