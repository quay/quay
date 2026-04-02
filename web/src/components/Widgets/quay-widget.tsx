import React from 'react';
import { SimpleServiceWidget } from './simple-service-widget';

const QuayWidget: React.FunctionComponent = () => {
  return (
    <>
      <SimpleServiceWidget
        id={4}
        body="Build, analyze, and distribute your container images."
        linkTitle="Quay.io"
        url="/quay/organization"
      />
    </>
  );
};

export default QuayWidget;
