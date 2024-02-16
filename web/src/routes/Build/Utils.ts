import {RepositoryBuildPhase} from 'src/resources/BuildResource';

export function getBuildMessage(phase: string): string {
  let message: string;
  switch (phase as RepositoryBuildPhase) {
    case null:
    case undefined:
      message = '';
      break;

    case RepositoryBuildPhase.CANNOT_LOAD:
      message = 'Cannot load build status';
      break;

    case RepositoryBuildPhase.STARTING:
    case RepositoryBuildPhase.INITIALIZING:
      message = 'Starting Dockerfile build';
      break;

    case RepositoryBuildPhase.WAITING:
      message = 'Waiting for available build worker';
      break;

    case RepositoryBuildPhase.UNPACKING:
      message = 'Unpacking build package';
      break;

    case RepositoryBuildPhase.PULLING:
      message = 'Pulling base image';
      break;

    case RepositoryBuildPhase.BUILDING:
      message = 'Building image from Dockerfile';
      break;

    case RepositoryBuildPhase.CHECKING_CACHE:
      message = 'Looking up cached images';
      break;

    case RepositoryBuildPhase.PRIMING_CACHE:
      message = 'Priming cache for build';
      break;

    case RepositoryBuildPhase.BUILD_SCHEDULED:
      message = 'Preparing build node';
      break;

    case RepositoryBuildPhase.PUSHING:
      message = 'Pushing image built from Dockerfile';
      break;

    case RepositoryBuildPhase.COMPLETE:
      message = 'Dockerfile build completed and pushed';
      break;

    case RepositoryBuildPhase.ERROR:
      message = 'Dockerfile build failed';
      break;

    case RepositoryBuildPhase.EXPIRED:
      message =
        'Build did not complete after 3 attempts. Re-submit this build to try again.';
      break;

    case RepositoryBuildPhase.INTERNAL_ERROR:
      message =
        'An internal system error occurred while building; ' +
        'the build will be retried in the next few minutes.';
      break;

    case RepositoryBuildPhase.CANCELLED:
      message = 'This build was previously cancelled.';
      break;

    case RepositoryBuildPhase.INCOMPLETE:
      message = 'This build was not completed.';
      break;

    default:
      throw new Error(`Invalid build phase: ${phase.toString()}`);
  }

  return message;
}

export function getCompletedBuildPhases() {
  return [
    RepositoryBuildPhase.COMPLETE,
    RepositoryBuildPhase.ERROR,
    RepositoryBuildPhase.EXPIRED,
    RepositoryBuildPhase.CANCELLED,
    RepositoryBuildPhase.INTERNAL_ERROR,
  ];
}
