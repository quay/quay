import { NgModule } from 'ng-metadata/core';
import { INJECTED_CONFIG, INJECTED_FEATURES, INJECTED_ENDPOINTS } from "./constants/injected-values.constant";
import { NAME_PATTERNS } from "./constants/name-patterns.constant";
import * as Raven from "raven-js";



var quayDependencies: string[] = [
  'chieffancypants.loadingBar',
  'cfp.hotkeys',
  'angular-tour',
  'restangular',
  'angularMoment',
  'mgcrea.ngStrap',
  'ngCookies',
  'ngSanitize',
  'angular-md5',
  'pasvaz.bindonce',
  'ansiToHtml',
  'core-ui',
  'ngTagsInput',
];

if (INJECTED_CONFIG && (INJECTED_CONFIG.MIXPANEL_KEY ||
  INJECTED_CONFIG.MUNCHKIN_KEY ||
  INJECTED_CONFIG.GOOGLE_ANALYTICS_KEY)) {
  quayDependencies.push('angulartics');
}
if (INJECTED_CONFIG && INJECTED_CONFIG.MIXPANEL_KEY) {
  quayDependencies.push('angulartics.mixpanel');
}
if (INJECTED_CONFIG && INJECTED_CONFIG.GOOGLE_ANALYTICS_KEY) {
  quayDependencies.push('angulartics.google.analytics');
}
if (INJECTED_CONFIG && INJECTED_CONFIG.RECAPTCHA_SITE_KEY) {
  quayDependencies.push('vcRecaptcha');
}


/**
 * Module for application-wide configuration.
 */
@NgModule({
  imports: quayDependencies,
  declarations: [],
  providers: [
    provideConfig,
    { provide: 'INJECTED_CONFIG', useValue: INJECTED_CONFIG },
    { provide: 'INJECTED_FEATURES', useValue: INJECTED_FEATURES },
    { provide: 'INJECTED_ENDPOINTS', useValue: INJECTED_ENDPOINTS },
    { provide: 'NAME_PATTERNS', useValue: NAME_PATTERNS },
  ]
})
export class QuayConfigModule {

}


/**
 * Provider function for the application configuration.
 * See https://hotell.gitbooks.io/ng-metadata/content/docs/recipes/startup-logic.html
 */
provideConfig.$inject = [
  '$provide',
  '$injector',
  'cfpLoadingBarProvider',
  '$tooltipProvider',
  '$compileProvider',
  'RestangularProvider',
];
function provideConfig($provide: ng.auto.IProvideService,
  $injector: ng.auto.IInjectorService,
  cfpLoadingBarProvider: any,
  $tooltipProvider: any,
  $compileProvider: ng.ICompileProvider,
  RestangularProvider: any): void {
  cfpLoadingBarProvider.includeSpinner = false;

  // decorate the tooltip getter
  var tooltipFactory: any = $tooltipProvider.$get[$tooltipProvider.$get.length - 1];
  $tooltipProvider.$get[$tooltipProvider.$get.length - 1] = function ($window: ng.IWindowService) {
    if ('ontouchstart' in $window) {
      const existing: any = tooltipFactory.apply(this, arguments);

      return function (element) {
        // Note: We only disable bs-tooltip's themselves. $tooltip is used for other things
        // (such as the datepicker), so we need to be specific when canceling it.
        if (element !== undefined && element.attr('bs-tooltip') == null) {
          return existing.apply(this, arguments);
        }
      };
    }

    return tooltipFactory.apply(this, arguments);
  };

  if (!INJECTED_CONFIG['DEBUG']) {
    $compileProvider.debugInfoEnabled(false);
  }

  // Configure compile provider to add additional URL prefixes to the sanitization list. We use
  // these on the Contact page.
  $compileProvider.aHrefSanitizationWhitelist(/^\s*(https?|ftp|mailto|tel|irc):/);

  // Configure the API provider.
  RestangularProvider.setBaseUrl('/api/v1/');

  // Configure analytics.
  if (INJECTED_CONFIG && INJECTED_CONFIG.MIXPANEL_KEY) {
    let $analyticsProvider: any = $injector.get('$analyticsProvider');
    $analyticsProvider.virtualPageviews(true);
  }

  // Configure sentry.
  if (INJECTED_CONFIG && INJECTED_CONFIG.SENTRY_PUBLIC_DSN) {
    $provide.decorator("$exceptionHandler", function ($delegate) {
      return function (ex, cause) {
        $delegate(ex, cause);
        Raven.captureException(ex, { extra: { cause: cause } });
      };
    });
  }
}
