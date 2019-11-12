import { Input, Component, Inject } from 'ng-metadata/core';
import * as moment from "moment";


/**
 * A component that allows for selecting a time duration.
 */
@Component({
  selector: 'duration-input',
  templateUrl: '/static/js/directives/ui/duration-input/duration-input.component.html'
})
export class DurationInputComponent implements ng.IComponentController {

  @Input('<') public min: string;
  @Input('<') public max: string;
  @Input('=?') public value: string;
  @Input('=?') public seconds: number;

  private min_s: number;
  private max_s: number;

  constructor(@Inject('$scope') private $scope: ng.IScope) {

  }

  public $onInit(): void {
    // TODO: replace this.
    this.$scope.$watch(() => this.seconds, this.updateValue.bind(this));

    this.refresh();
  }

  public $onChanges(changes: ng.IOnChangesObject): void {
    this.refresh();
  }

  private updateValue(): void {
    this.value = `${this.seconds}s`;
  }

  private refresh(): void {
    this.min_s = this.toSeconds(this.min || '0s');
    this.max_s = this.toSeconds(this.max || '1h');

    if (this.value) {
      this.seconds = this.toSeconds(this.value || '0s');
    }
  }

  private durationExplanation(durationSeconds: string): string {
    return moment.duration(parseInt(durationSeconds), 's').humanize();
  }

  private toSeconds(durationStr: string): number {
    var number = durationStr.substring(0, durationStr.length - 1);
    var suffix = durationStr.substring(durationStr.length - 1);
    return moment.duration(parseInt(number), <moment.unitOfTime.Base>suffix).asSeconds();
  }
}
