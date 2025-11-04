import {ReactNode, useEffect, useState} from 'react';
import {FreshLoginModal} from 'src/components/modals/FreshLoginModal';
import {useGlobalFreshLogin} from 'src/hooks/UseGlobalFreshLogin';

interface AppWithFreshLoginProps {
  children: ReactNode;
}

export function AppWithFreshLogin({children}: AppWithFreshLoginProps) {
  const {isModalOpen, isLoading, error, handleVerify, handleCancel} =
    useGlobalFreshLogin();
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    const handleFreshLoginRequired = () => {
      setShowModal(true);
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
    await handleVerify(password);
    setShowModal(false);
  };

  const handleCancelWrapper = () => {
    handleCancel();
    setShowModal(false);
  };

  return (
    <>
      {children}
      <FreshLoginModal
        isOpen={showModal || isModalOpen}
        onVerify={handleVerifyWrapper}
        onCancel={handleCancelWrapper}
        isLoading={isLoading}
        error={error}
      />
    </>
  );
}
