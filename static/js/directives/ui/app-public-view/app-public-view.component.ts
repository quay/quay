import { Input, Component, Inject } from 'ng-metadata/core';


/**
 * A component that displays the public information associated with an application repository.
 */
@Component({
  selector: 'app-public-view',
  templateUrl: '/static/js/directives/ui/app-public-view/app-public-view.component.html'
})
export class AppPublicViewComponent {

  @Input('<') public repository: any;

  private settingsShown: number = 0;
  private logsShown: number = 0;

  constructor(@Inject('Config') private Config: any) {
    this.updateDescription = this.updateDescription.bind(this);
  }

  public showSettings(): void {
    this.settingsShown++;
  }

  public showLogs(): void {
    this.logsShown++;
  }

  private updateDescription(content: string) {
    this.repository.description = content;
    this.repository.put();
  }
}
