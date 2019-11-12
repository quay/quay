/**
 * Service which provides helper methods for retrieving the avatars displayed in the app.
 */
export abstract class AvatarService {

  /**
   * Retrieve URL for avatar image with given hash.
   * @param hash Avatar image hash.
   * @param size Avatar image size.
   * @param notFound URL parameter if avatar image is not found.
   * @return avatarURL The URL for the avatar image.
   */
  public abstract getAvatar(hash: string, size?: number, notFound?: string): string;

  /**
   * Compute the avatar image hash.
   * @param email Email for avatar user.
   * @param name Username for avatar user.
   * @return hash The hash for the avatar image.
   */
  public abstract computeHash(email?: string, name?: string): string;
}
