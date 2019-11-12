/**
 * Service which provides helper methods for reasoning about builds.
 */
export abstract class BuildService {

  /**
   * Determine if the given build is active.
   * @param build The build object.
   * @return isActive If the given build is active.
   */
  public abstract isActive(build: {phase: string}): boolean;

  /**
   * Generate a message based on a given phase.
   * @param phase The phase type.
   * @return buildMessage The message associated with the given phase.
   */
  public abstract getBuildMessage(phase: string): string;
}
