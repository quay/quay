import React from 'react';
import {Banner, Flex, FlexItem} from '@patternfly/react-core';
import {ExclamationTriangleIcon} from '@patternfly/react-icons';
import {useQuayState} from 'src/hooks/UseQuayState';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';

interface BannerContentProps {
  icon: React.ReactNode;
  children: React.ReactNode;
}

const BannerContent: React.FC<BannerContentProps> = ({icon, children}) => (
  <Flex
    spaceItems={{default: 'spaceItemsSm'}}
    justifyContent={{default: 'justifyContentCenter'}}
    alignItems={{default: 'alignItemsCenter'}}
  >
    <FlexItem>{icon}</FlexItem>
    <FlexItem>{children}</FlexItem>
  </Flex>
);

export default function SystemStatusBanner() {
  const {inReadOnlyMode, inAccountRecoveryMode} = useQuayState();
  const config = useQuayConfig();
  const registryName = config?.config?.REGISTRY_TITLE || 'Quay';

  return (
    <>
      {inReadOnlyMode && (
        <Banner
          variant="default"
          data-testid="readonly-mode-banner"
          screenReaderText="Read-only mode warning"
        >
          <BannerContent icon={<ExclamationTriangleIcon />}>
            <strong>{registryName}</strong> is currently in read-only mode.
            Pulls and other read-only operations will succeed but all other
            operations are currently suspended.
          </BannerContent>
        </Banner>
      )}
      {inAccountRecoveryMode && (
        <Banner
          variant="gold"
          data-testid="account-recovery-mode-banner"
          screenReaderText="Account recovery mode warning"
        >
          <BannerContent icon={<ExclamationTriangleIcon />}>
            <strong>{registryName}</strong> is currently in account recovery
            mode. This instance should only be used to link accounts to an
            external login service, e.g., Red Hat. Registry operations such as
            pushes/pulls will not work.
          </BannerContent>
        </Banner>
      )}
    </>
  );
}
