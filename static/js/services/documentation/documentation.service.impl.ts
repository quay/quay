import { DocumentationService } from './documentation.service';
import { Injectable, Inject } from 'ng-metadata/core';


@Injectable(DocumentationService.name)
export class DocumentationServiceImpl implements DocumentationService {
  private documentationRoot: string;
  private documentMap: object;

  constructor(@Inject('Config') private Config: any) {
    this.documentationRoot = Config['DOCUMENTATION_ROOT'];
    this.documentMap = {
      'builds.custom-trigger': 'html/use_red_hat_quay/setting_up_a_custom_git_trigger',
      'notifications.webhook': function (p) {
        if (!p['event']) {
          return `html/use_red_hat_quay/repository_notifications`;
        }
        return `html/use_red_hat_quay/repository_notifications#${p['event']}`;
      },
      'notifications': 'html/use_red_hat_quay/repository_notifications',
      'builds.tag-templating': 'https://github.com/quay/quay/blob/master/buildtrigger/basehandler.py#L81'
    };
  }

  public getUrl(documentId: string, parameters?: object): string {
    if (!this.documentMap[documentId]) {
      return '';
    }

    let generator = this.documentMap[documentId];
    if (typeof generator == 'string') {
      generator = (p) => this.documentMap[documentId]
    }

    let url = generator(parameters || {});
    if (url.indexOf('https://') != 0) {
      url = this.documentationRoot + url;
    }
    return url;
  }
}
