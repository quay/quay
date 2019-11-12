import { Input, Component, OnChanges, SimpleChanges, Output, EventEmitter } from 'ng-metadata/core';


/**
 * A component that allows the user to select the location of the Context in their source code repository.
 */
@Component({
  selector: 'context-path-select',
  templateUrl: '/static/js/directives/ui/context-path-select/context-path-select.component.html'
})
export class ContextPathSelectComponent implements OnChanges {

  @Input('<') public currentContext: string = '';
  @Input('<') public contexts: string[];
  @Output() public contextChanged: EventEmitter<ContextChangeEvent> = new EventEmitter();
  public isValidContext: boolean;
  private isUnknownContext: boolean = true;
  private selectedContext: string | null = null;

  public ngOnChanges(changes: SimpleChanges): void {
    this.isValidContext = this.checkContext(this.currentContext, this.contexts);
  }

  public setContext(context: string): void {
    this.currentContext = context;
    this.selectedContext = null;
    this.isValidContext = this.checkContext(context, this.contexts);

    this.contextChanged.emit({contextDir: context, isValid: this.isValidContext});
  }

  public setSelectedContext(context: string): void {
    this.currentContext = context;
    this.selectedContext = context;
    this.isValidContext = this.checkContext(context, this.contexts);

    this.contextChanged.emit({contextDir: context, isValid: this.isValidContext});
  }

  private checkContext(context: string = '', contexts: string[] = []): boolean {
    this.isUnknownContext = false;
    var isValidContext: boolean = false;

    if (context.length > 0 && context[0] === '/') {
      isValidContext = true;
      this.isUnknownContext = contexts.indexOf(context) != -1;
    }
    return isValidContext;
  }
}


/**
 * Build context changed event.
 */
export type ContextChangeEvent = {
  contextDir: string;
  isValid: boolean;
};
