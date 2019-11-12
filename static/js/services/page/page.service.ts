/**
 * Manages the creation and retrieval of pages (route + controller)
 */
export abstract class PageService implements ng.IServiceProvider {

  /**
   * Create a page.
   * @param pageName The name of the page.
   * @param templateName The file name of the template.
   * @param controller Controller for the page.
   * @param flags Additional flags passed to route provider.
   * @param profiles Available profiles.
   */
  public abstract create(pageName: string,
                         templateName: string,
                         controller?: any,
                         flags?: any,
                         profiles?: string[]): void;

  /**
   * Retrieve a registered page.
   * @param pageName The name of the page.
   * @param profiles Available profiles to search.
   */
  public abstract get(pageName: string, profiles: QuayPageProfile[]): [QuayPageProfile, QuayPage] | null;

  /**
   * Provide the service instance.
   * @return pageService The singleton service instance.
   */
  public abstract $get(): PageService;
}


/**
 * A type representing a registered application page.
 */
export type QuayPage = {
  name: string;
  controller: ng.IController;
  templateName: string,
  flags: {[key: string]: any};
};


/**
 * Represents a page profile type.
 */
export type QuayPageProfile = {
  id: string;
  templatePath: string;
};

