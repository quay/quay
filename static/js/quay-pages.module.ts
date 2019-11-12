import { PageServiceImpl } from './services/page/page.service.impl';
import * as angular from 'angular';


/**
 * TODO: Needed for non-TypeScript components/services to register themselves. Remove once they are migrated.
 */
export const QuayPagesModule: ng.IModule = angular.module('quayPages', [])
  .constant('pages', new PageServiceImpl());
