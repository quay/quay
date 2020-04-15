/**
 * Service which provides helper methods for retrieving documentation links.
 */
export abstract class DocumentationService {
  /**
   * Returns the documentation URL for the given document ID.
   * @param documentId The ID of the documentation to return.
   * @param parameters Optional parameters for the document.
   * @return url The documentation URL.
   */
  public abstract getUrl(documentId: string, parameters?: object): string;
}
