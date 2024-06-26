import {useEffect, useState} from 'react';
import {PageSection, PageSectionVariants, Title} from '@patternfly/react-core';
import {QuayBreadcrumb} from 'src/components/breadcrumb/Breadcrumb';

interface SuperuserListHeaderProps {}
function SuperuserListHeader(props: SuperuserListHeaderProps) {
  return (
    <>
      <QuayBreadcrumb />
      <PageSection variant={PageSectionVariants.light} hasShadowBottom>
        <div className="co-m-nav-title--row">
          <Title headingLevel="h1">Users</Title>
        </div>
      </PageSection>
    </>
  );
}

export default function SuperuserUsersList(props: SuperuserListProps) {
  return <>sample</>;
}

interface SuperuserListProps {}
