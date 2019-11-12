import { BuildService } from './build.service';
import { Injectable } from 'ng-metadata/core';


@Injectable(BuildService.name)
export class BuildServiceImpl implements BuildService {

  private inactivePhases: string[] = ['complete', 'error', 'expired', 'cancelled'];

  public isActive(build: {phase: string}): boolean {
    return this.inactivePhases.indexOf(build.phase) == -1;
  }

  public getBuildMessage(phase: string): string {
    var message: string;
    switch (phase) {
      case null:
      case undefined:
        message = '';
        break;

      case 'cannot_load':
        message = 'Cannot load build status';
        break;

      case 'starting':
      case 'initializing':
        message = 'Starting Dockerfile build';
        break;

      case 'waiting':
        message = 'Waiting for available build worker';
        break;

      case 'unpacking':
        message = 'Unpacking build package';
        break;

      case 'pulling':
        message = 'Pulling base image';
        break;

      case 'building':
        message = 'Building image from Dockerfile';
        break;

      case 'checking-cache':
        message = 'Looking up cached images';
        break;

      case 'priming-cache':
        message = 'Priming cache for build';
        break;

      case 'build-scheduled':
        message = 'Preparing build node';
        break;

      case 'pushing':
        message = 'Pushing image built from Dockerfile';
        break;

      case 'complete':
        message = 'Dockerfile build completed and pushed';
        break;

      case 'error':
        message = 'Dockerfile build failed';
        break;

      case 'expired':
        message = 'Build did not complete after 3 attempts. Re-submit this build to try again.';
        break;

      case 'internalerror':
        message = 'An internal system error occurred while building; ' +
                  'the build will be retried in the next few minutes.';
        break;

      case 'cancelled':
        message = 'This build was previously cancelled.';
        break;

      case 'incomplete':
        message = 'This build was not completed.';
        break;

      default:
        throw new Error(`Invalid build phase: ${phase.toString()}`);
    }

    return message;
  }
}
