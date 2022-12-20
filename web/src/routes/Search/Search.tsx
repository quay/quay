import {
  Page,
  PageSection,
  PageSectionVariants,
  Title,
} from '@patternfly/react-core';
import * as React from 'react';

export default function Search() {
  return (
    <Page>
      <PageSection variant={PageSectionVariants.light} hasShadowBottom>
        <div className="co-m-nav-title--row">
          <Title headingLevel="h1">Search</Title>
        </div>
      </PageSection>

      <PageSection>
        <PageSection variant={PageSectionVariants.light}></PageSection>
      </PageSection>
    </Page>
  );
}
