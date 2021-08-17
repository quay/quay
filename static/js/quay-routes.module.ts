import { RouteBuilderImpl } from './services/route-builder/route-builder.service.impl';
import { RouteBuilder } from './services/route-builder/route-builder.service';
import { PageService } from './services/page/page.service';
import { NgModule } from 'ng-metadata/core';
import { INJECTED_FEATURES } from './constants/injected-values.constant';
import { QuayPagesModule } from './quay-pages.module';


/**
 * Module containing client-side routing configuration.
 */
@NgModule({
  imports: [
    QuayPagesModule.name,
    'ngRoute',
  ],
  declarations: [],
  providers: [
    provideRoutes,
  ],
})
export class QuayRoutesModule {

}


/**
 * Provider function for setting up client-side routing.
 * See https://hotell.gitbooks.io/ng-metadata/content/docs/recipes/startup-logic.html
 */
provideRoutes.$inject = [
  '$routeProvider',
  '$locationProvider',
  'pages',
];
function provideRoutes($routeProvider: ng.route.IRouteProvider,
                       $locationProvider: ng.ILocationProvider,
                       pageServiceProvider: PageService): void {
  $locationProvider.html5Mode(true);

  // WARNING WARNING WARNING
  // If you add a route here, you must add a corresponding route in thr endpoints/web.py
  // index rule to make sure that deep links directly deep into the app continue to work.
  // WARNING WARNING WARNING

  const routeBuilder: RouteBuilder = new RouteBuilderImpl($routeProvider, pageServiceProvider.$get());

  if (INJECTED_FEATURES.SUPER_USERS) {
    // QE Management
    routeBuilder.route('/superuser/', 'superuser')
        .route('/incomplete-setup/', 'incomplete-setup');
  }

  routeBuilder
    // Search
    .route('/search', 'search')

    // Application View
    .route('/application/:namespace/:name', 'app-view')

    // Repo List
    .route('/application/', 'app-list')

    // Image View
    .route('/repository/:namespace/:name*\/manifest/:manifest_digest', 'manifest-view')

    // Repo Build View
    .route('/repository/:namespace/:name*\/build/:buildid', 'build-view')

    // Repo Trigger View
    .route('/repository/:namespace/:name*\/trigger/:triggerid', 'trigger-setup')

    // Create repository notification
    .route('/repository/:namespace/:name*\/create-notification', 'create-repository-notification')

    // Repository View
    .route('/repository/:namespace/:name*\/tag/:tag', 'repo-view')
    .route('/repository/:namespace/:name*', 'repo-view')

    // Repo List
    .route('/repository/', 'repo-list')

    // Organizations
    .route('/organizations/', 'organizations')

    // New Organization
    .route('/organizations/new/', 'new-organization')

    // View Organization
    .route('/organization/:orgname', 'org-view')

    // View Organization Team
    .route('/organization/:orgname/teams/:teamname', 'team-view')

    // Organization View Application
    .route('/organization/:orgname/application/:clientid', 'manage-application')

    // View Organization Billing
    .route('/organization/:orgname/billing', 'billing')

    // View Organization Billing Invoices
    .route('/organization/:orgname/billing/invoices', 'invoices')

    // View User
    .route('/user/:username', 'user-view')

    // View User Billing
    .route('/user/:username/billing', 'billing')

    // View User Billing Invoices
    .route('/user/:username/billing/invoices', 'invoices')

    // Sign In
    .route('/signin/', 'signin')

    // New Repository
    .route('/new/', 'new-repo')

    // Plans
    .route('/plans/', 'plans')

    // Tutorial
    .route('/tutorial/', 'tutorial')

    // Contact
    .route('/contact/', 'contact')

    // About
    .route('/about/', 'about')

    // Security
    .route('/security/', 'security')

    // Change username
    .route('/updateuser', 'update-user')

    // Landing Page
    .route('/', 'landing')

    // Tour
    .route('/tour/', 'tour')
    .route('/tour/features', 'tour')
    .route('/tour/organizations', 'tour')
    .route('/tour/enterprise', 'tour')

    // Confirm Invite
    .route('/confirminvite', 'confirm-invite')

    // 404/403
    .route('/:catchall', 'error-view')
    .route('/:catch/:all', 'error-view')
    .route('/:catch/:all/:things', 'error-view')
    .route('/:catch/:all/:things/:here', 'error-view');
}
