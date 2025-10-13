import {PageSection, Title} from '@patternfly/react-core';

export default function Search() {
  return (
    <>
      <PageSection hasBodyWrapper={false} hasShadowBottom>
        <div className="co-m-nav-title--row">
          <Title headingLevel="h1">Search</Title>
        </div>
      </PageSection>

      <PageSection hasBodyWrapper={false}>
        <PageSection hasBodyWrapper={false}></PageSection>
      </PageSection>
    </>
  );
}
