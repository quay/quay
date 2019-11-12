import { Input, Component, Inject } from 'ng-metadata/core';

/**
 * A component which displays an image's command, nicely formatted.
 */
@Component({
  selector: 'image-command',
  templateUrl: '/static/js/directives/ui/image-command/image-command.component.html',
})
export class ImageCommandComponent {
  @Input('<') public command: string;

  private getDockerfileCommand(command: string[]): string {
    if (!command || !command.length) { return ''; }
    command = command.join(' ').split(' ');

    // ["/bin/sh", "-c", "#(nop)", "RUN", "foo"]
    if (command[0] != '/bin/sh' || command[1] != '-c') { return ''; }

    if (command[2].trim() != '#(nop)') {
      return 'RUN ' + command.slice(2).join(' ');
    }

    return command.slice(3).join(' ');
  };
}
