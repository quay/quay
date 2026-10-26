import {Breadcrumb, BreadcrumbItem} from '@patternfly/react-core';
import {Link} from 'react-router-dom';
import {getPlanInformationPath} from 'src/libs/billing';

type Props = {organizationName: string; currentPage: string};

export function BillingBreadcrumb({organizationName, currentPage}: Props) {
  return (
    <Breadcrumb className="pf-v6-u-mb-lg" aria-label="Billing navigation">
      <BreadcrumbItem>
        <Link to={`/organization/${encodeURIComponent(organizationName)}`}>
          {organizationName}
        </Link>
      </BreadcrumbItem>
      <BreadcrumbItem>
        <Link to={getPlanInformationPath(organizationName)}>
          Plan information
        </Link>
      </BreadcrumbItem>
      <BreadcrumbItem isActive>{currentPage}</BreadcrumbItem>
    </Breadcrumb>
  );
}
