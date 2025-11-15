import {ReactNode, useEffect, useState} from 'react';
import {FreshLoginModal} from 'src/components/modals/FreshLoginModal';
import {useGlobalFreshLogin} from 'src/hooks/UseGlobalFreshLogin';
import {AlertVariant, useUI} from 'src/contexts/UIContext';

interface AppWithFreshLoginProps {
  children: ReactNode;
}

export function AppWithFreshLogin({children}: AppWithFreshLoginProps) {
  const {isLoading, handleVerify, handleCancel} = useGlobalFreshLogin();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const {addAlert} = useUI();

  useEffect(() => {
    const handleFreshLoginRequired = () => {
      setIsModalOpen(true);
    };

    window.addEventListener('freshLoginRequired', handleFreshLoginRequired);
    return () => {
      window.removeEventListener(
        'freshLoginRequired',
        handleFreshLoginRequired,
      );
    };
  }, []);

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
