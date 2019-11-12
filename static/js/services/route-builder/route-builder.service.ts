/**
 * Constructs client-side routes.
 */
export abstract class RouteBuilder {

  /**
   * Configure the redirect route.
   * @param options Configuration options.
   */
  public abstract otherwise(options: any): void;

  /**
   * Register a route.
   * @param path The URL of the route.
   * @param pagename The name of the page to associate with this route.
   */
  public abstract route(path: string, pagename: string): RouteBuilder;
}
