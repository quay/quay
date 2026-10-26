import {useParams} from 'react-router-dom';
import {NavigationPath} from './NavigationPath';
import {ChangePlan} from './OrganizationsList/Organization/Tabs/Settings/ChangePlan';
import {InvoiceList} from './OrganizationsList/Organization/Tabs/Settings/InvoiceList';
import {SubscriptionList} from './OrganizationsList/Organization/Tabs/Settings/SubscriptionList';

function ChangePlanRoute() {
  const {organizationName} = useParams<{organizationName: string}>();
  return <ChangePlan organizationName={organizationName} />;
}

function InvoiceListRoute() {
  const {organizationName} = useParams<{organizationName: string}>();
  return <InvoiceList organizationName={organizationName} />;
}

function SubscriptionListRoute() {
  const {organizationName} = useParams<{organizationName: string}>();
  return <SubscriptionList organizationName={organizationName} />;
}

// Both shells expose the destinations linked from the shared billing settings.
export const billingNavigationRoutes = [
  {path: NavigationPath.organizationPlans, Component: <ChangePlanRoute />},
  {path: NavigationPath.invoiceList, Component: <InvoiceListRoute />},
  {path: NavigationPath.subscriptionList, Component: <SubscriptionListRoute />},
];
