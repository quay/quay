import { INJECTED_CONFIG } from "./constants/injected-values.constant";


/**
 * Provider function for the application runtime configuration.
 * See https://hotell.gitbooks.io/ng-metadata/content/docs/recipes/startup-logic.html
 */
provideRun.$inject = [
  '$rootScope',
  'Restangular',
  'PlanService',
  '$http',
  'CookieService',
  'UserService',
  'StateService',
  'Features',
  '$anchorScroll',
  'MetaService',
];
export function provideRun($rootScope: QuayRunScope,
                           restangular: any,
                           planService: any,
                           $http: ng.IHttpService,
                           cookieService: any,
                           userService: any,
                           stateService: any,
                           features: any,
                           $anchorScroll: ng.IAnchorScrollService,
                           metaService: any): void {
  const defaultTitle: string = INJECTED_CONFIG['REGISTRY_TITLE'] || 'Quay Container Registry';

  if ((<any>window).__registry_state == 'readonly') {
    stateService.setInReadOnlyMode();
  }

  if ((<any>window).__account_recovery_mode) {
    stateService.setInAccountRecoveryMode();
  }

  // Handle session security.
  restangular.setDefaultHeaders({
    'X-Requested-With': 'XMLHttpRequest',
    'X-CSRF-Token': (<any>window).__token || ''
  });

  restangular.setResponseInterceptor(function(data, operation, what, url, response, deferred) {
    var headers = response.headers();
    if (headers['x-next-csrf-token']) {
      (<any>window).__token = headers['x-next-csrf-token'];
      restangular.setDefaultHeaders({
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRF-Token': (<any>window).__token || ''
      });
    }
    return data;
  });

  // Handle session expiration.
  restangular.setErrorInterceptor(function(response) {
    if (response !== undefined && response.status == 503) {
      if (response.data['errors'] &&
          response.data['errors'].length > 0 &&
          response.data['errors'][0]['code'] == "READ_ONLY_MODE") {
        stateService.setInReadOnlyMode();
        (<any>$('#readOnlyService')).modal({});
      } else {
        (<any>$('#cannotContactService')).modal({});
      }
      return false;
    }

    if (response !== undefined && response.status == 500) {
      window.location.href = '/500';
      return false;
    }

    if (response !== undefined && !response.data) {
      return true;
    }

    const invalid_token: boolean = response.data['title'] == 'invalid_token' ||
                                   response.data['error_type'] == 'invalid_token';
    if (response !== undefined &&
        response.status == 401 &&
        invalid_token &&
        response.data['session_required'] !== false) {
      (<any>$('#sessionexpiredModal')).modal({});
      return false;
    }

    return true;
  });

  // Check if we need to redirect based on a previously chosen plan.
  const result: boolean = planService.handleNotedPlan();

  // Check to see if we need to show a redirection page.
  const redirectUrl: string = cookieService.get('quay.redirectAfterLoad');
  cookieService.clear('quay.redirectAfterLoad');

  if (!result && redirectUrl && redirectUrl.indexOf((<any>window).location.href) == 0) {
    (<any>window).location = redirectUrl;
    return;
  }

  $rootScope.$watch('description', (description: string) => {
    if (!description) {
      description = `Hosted private Docker repositories. Includes full user management and history. 
                     Free for public repositories.`;
    }

    // Note: We set the content of the description tag manually here rather than using Angular binding
    // because we need the <meta> tag to have a default description that is not of the form "{{ description }}",
    // we read by tools that do not properly invoke the Angular code.
    $('#descriptionTag').attr('content', description);
  });

  $rootScope.$on('$routeChangeSuccess', (event, current, previous) => {
    $rootScope.current = current.$$route;
    $rootScope.currentPage = current;
    $rootScope.pageClass = '';

    if (!current.$$route) { return; }

    var pageClass: string | Function = current.$$route.pageClass || '';
    if (typeof pageClass != 'string') {
      pageClass = pageClass(features);
    }

    $rootScope.pageClass = pageClass;
    $rootScope.newLayout = !!current.$$route.newLayout;
    $rootScope.fixFooter = !!current.$$route.fixFooter;

    $anchorScroll();
  });

  // Listen for route changes and update the title and description accordingly.
  $rootScope.$on('$routeChangeSuccess', async(event, current, previous) => {
    const title = await metaService.getTitle(current);    
    const description = await metaService.getDescription(current);

    $rootScope.title = title || defaultTitle;
    if ($rootScope.description != description) {
      $rootScope.description = description;
    }
  });

  var initallyChecked: boolean = false;
  (<any>window).__isLoading = function() {
    if (!initallyChecked) {
      initallyChecked = true;
      return true;
    }
    return $http.pendingRequests.length > 0;
  };

  // Load the inital user information.
  userService.load();
}


interface QuayRunScope extends ng.IRootScopeService {
  currentPage: any;
  current: any;
  title: any;
  description: string;
  pageClass: any;
  newLayout: any;
  fixFooter: any;
}
