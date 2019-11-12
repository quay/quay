import { Input, Component, Inject } from 'ng-metadata/core';


/**
 * A component that displays the icon of a channel.
 */
@Component({
  selector: 'channel-icon',
  templateUrl: '/static/js/directives/ui/channel-icon/channel-icon.component.html',
})
export class ChannelIconComponent {
  @Input('<') public name: string;
  private colors: any;

  constructor(@Inject('Config') Config: any, @Inject('md5') private md5: any) {
    this.colors = Config['CHANNEL_COLORS'];
  }

  private initial(name: string): string {
    if (name == 'alpha') {
      return 'α';
    }
    if (name == 'beta') {
      return 'β';
    }
    if (name == 'stable') {
      return 'S';
    }
    return name[0].toUpperCase();
  }

  private color(name: string): string {
    if (name == 'alpha') {
      return this.colors[0];
    }
    if (name == 'beta') {
      return this.colors[1];
    }
    if (name == 'stable') {
      return this.colors[2];
    }

    var hash: string = this.md5.createHash(name);
    var num: number = parseInt(hash.substr(0, 4));
    return this.colors[num % this.colors.length];
  }
}
