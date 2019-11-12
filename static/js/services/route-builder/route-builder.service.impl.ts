import { RouteBuilder } from './route-builder.service';
import { Injectable, Inject } from 'ng-metadata/core';
import { PageService, QuayPage, QuayPageProfile } from '../page/page.service';


@Injectable(RouteBuilder.name)
export class RouteBuilderImpl implements RouteBuilder {

  public currentProfile: string = 'layout';
  public profiles: QuayPageProfile[] = [
    // Start with the old pages (if we asked for it).
    {id: 'old-layout', templatePath: '/static/partials/'},
    // Fallback back combined new/existing pages.
    {id: 'layout', templatePath: '/static/partials/'}
  ];


  constructor(@Inject('routeProvider') private routeProvider: ng.route.IRouteProvider,
              @Inject('pages') private pages: PageService) {
    for (let i = 0; i < this.profiles.length; ++i) {
      if (this.profiles[i].id == this.currentProfile) {
        this.profiles = this.profiles.slice(i);
        break;
      }
    }
  }

  public otherwise(options: any): void {
    this.routeProvider.otherwise(options);
  }

  public route(path: string, pagename: string): RouteBuilder {
    // Lookup the page, matching our lists of profiles.
    var pair = this.pages.get(pagename, this.profiles);
    if (!pair) {
      throw Error('Unknown page: ' + pagename);
    }

    // Create the route.
    var foundProfile = pair[0];
    var page = pair[1];
    var templateUrl = foundProfile.templatePath + page.templateName;

    var options = page.flags || {};
    options['templateUrl'] = templateUrl;
    options['reloadOnSearch'] = false;
    options['controller'] = page.controller;

    this.routeProvider.when(path, options);

    return this;
  }
}
