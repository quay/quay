import {ReactNode, useEffect, useState} from 'react';
import {FreshLoginModal} from 'src/components/modals/FreshLoginModal';
import {useGlobalFreshLogin} from 'src/hooks/UseGlobalFreshLogin';

interface AppWithFreshLoginProps {
  children: ReactNode;
}

export function AppWithFreshLogin({children}: AppWithFreshLoginProps) {
  const {isLoading, error, handleVerify, handleCancel} = useGlobalFreshLogin();
  const [isModalOpen, setIsModalOpen] = useState(false);

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
    await handleVerify(password);
    setIsModalOpen(false);
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
        error={error}
      />
    </>
  );
}
