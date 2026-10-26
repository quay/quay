import React, {Suspense} from 'react';
import {LoadingPage} from './LoadingPage';

interface SuspenseLoaderProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export const SuspenseLoader: React.FC<SuspenseLoaderProps> = ({
  children,
  fallback = <LoadingPage />,
}): React.ReactElement => <Suspense fallback={fallback}>{children}</Suspense>;
