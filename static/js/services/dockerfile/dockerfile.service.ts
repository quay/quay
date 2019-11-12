/**
 * Service which provides helper methods for extracting information out from a Dockerfile
 * or an archive containing a Dockerfile.
 */
export abstract class DockerfileService {

  /**
   * Retrieve Dockerfile from given file.
   * @param file Dockerfile or archive file containing Dockerfile.
   * @return promise Promise which resolves to new DockerfileInfo instance or rejects with error message.
   */
  public abstract getDockerfile(file: any): Promise<DockerfileInfo | string>;
}


/**
 * Model representing information about a specific Dockerfile.
 */
export abstract class DockerfileInfo {

  /**
   * Extract the registry base image from the Dockerfile contents.
   * @return registryBaseImage The registry base image.
   */
  public abstract getRegistryBaseImage(): string | null;

  /**
   * Extract the base image from the Dockerfile contents.
   * @return baseImage The base image.
   */
  public abstract getBaseImage(): string | null;

  /**
   * Extract the base image and tag from the Dockerfile contents.
   * @return baseImageAndTag The base image and tag.
   */
  public abstract getBaseImageAndTag(): string | null;
}
