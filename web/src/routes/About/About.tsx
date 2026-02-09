import React from 'react';
import {PageSection, Content, ContentVariants} from '@patternfly/react-core';
import TheBasics from './TheBasics';
import PackagesTable from './PackagesTable';
import './css/About.scss';

export const About: React.FC = () => {
  return (
    <>
      <PageSection hasBodyWrapper={false}>
        <Content>
          <Content component={ContentVariants.h1}>About Us</Content>
        </Content>
      </PageSection>
      <PageSection hasBodyWrapper={false} className="about-page">
        <TheBasics />
        <PackagesTable />
      </PageSection>
    </>
  );
};

export default About;
