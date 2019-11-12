import { Input, Component, Inject } from 'ng-metadata/core';
import './dockerfile-command.component.css';

/**
 * A component which displays a Dockerfile command, nicely formatted.
 */
@Component({
  selector: 'dockerfile-command',
  templateUrl: '/static/js/directives/ui/dockerfile-command/dockerfile-command.component.html',
})
export class DockerfileCommandComponent {
  @Input('<') public command: string;

  private registryHandlers: {[domain: string]: Function};

  constructor (@Inject('Config') Config: any, @Inject('UtilService') private utilService: any) {
    var registryHandlers = {
      'quay.io': function(pieces) {
        var rnamespace =  pieces[pieces.length - 2];
        var rname = pieces[pieces.length - 1].split(':')[0];
        return '/repository/' + rnamespace + '/' + rname + '/';
      },

      '': function(pieces) {
        var rnamespace = pieces.length == 1 ? '_' : 'u/' + pieces[0];
        var rname = pieces[pieces.length - 1].split(':')[0];
        return 'https://registry.hub.docker.com/' + rnamespace + '/' + rname + '/';
      }
    };

    registryHandlers[Config.getDomain()] = registryHandlers['quay.io'];
    this.registryHandlers = registryHandlers;
  }

  private getCommandKind(command: string): string {
    command = command.trim();
    if (!command) { return ''; }

    var space = command.indexOf(' ');
    return command.substring(0, space);
  }

  private getCommandTitleHtml(command: string): string {
    command = command.trim();
    if (!command) { return ''; }

    var kindHandlers = {
      'FROM': (command) => {
        var parts = command.split(' ');
        var pieces = parts[0].split('/');
        var registry = pieces.length < 3 ? '' : pieces[0];
        if (!this.registryHandlers[registry]) {
          return command;
        }

        return '<a href="' + this.registryHandlers[registry](pieces) + '" target="_blank">' + parts[0] + '</a> ' + (parts.splice(1).join(' '));
      }
    };

    var space = command.indexOf(' ');
    if (space <= 0) {
      return this.utilService.textToSafeHtml(command);
    }

    var kind = this.getCommandKind(command);
    var sanitized = this.utilService.textToSafeHtml(command.substring(space + 1));

    var handler = kindHandlers[kind || ''];
    if (handler) {
      return handler(sanitized);
    } else {
      return sanitized;
    }
  }
}
