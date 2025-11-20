import React from 'react';
import {
  PageSection,
  PageSectionVariants,
  Text,
  TextContent,
  TextVariants,
} from '@patternfly/react-core';
import TheBasics from './TheBasics';
import PackagesTable from './PackagesTable';
import './css/About.scss';

export const About: React.FC = () => {
  return (
    <>
      <PageSection variant={PageSectionVariants.light}>
        <TextContent>
          <Text component={TextVariants.h1}>About Us</Text>
        </TextContent>
      </PageSection>
      <PageSection variant={PageSectionVariants.default} className="about-page">
        <TheBasics />
        <PackagesTable />
      </PageSection>
    </>
  );
};

export default About;
