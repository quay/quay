import { Injectable } from 'ng-metadata/core';
import { PageService, QuayPage, QuayPageProfile } from './page.service';


@Injectable(PageService.name)
export class PageServiceImpl implements ng.IServiceProvider {

  private pages: {[pageName: string]: QuayPage} = {};

  public create(pageName: string,
                templateName: string,
                controller?: any,
                flags: any = {},
                profiles: string[] = ['old-layout', 'layout']): void {
    for (var i = 0; i < profiles.length; ++i) {
      this.pages[profiles[i] + ':' + pageName] = {
        'name': pageName,
        'controller': controller,
        'templateName': templateName,
        'flags': flags
      };
    }
  }

  public get(pageName: string, profiles: QuayPageProfile[]): [QuayPageProfile, QuayPage] | null {
    for (let i = 0; i < profiles.length; ++i) {
      var current = profiles[i];
      var key = current.id + ':' + pageName;
      var page = this.pages[key];
      if (page) {
        return [current, page];
      }
    }

    return null;
  }

  public $get(): PageService {
    return this;
  }
}
