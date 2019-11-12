import { Input, Output, Directive, Inject, AfterContentInit, EventEmitter, HostListener } from 'ng-metadata/core';
import * as $ from 'jquery';


/**
 * Directive which decorates an <input> with a typeahead autocomplete.
 */
@Directive({
  selector: '[typeahead]',
})
export class TypeaheadDirective implements AfterContentInit {

  @Input('taDisplayKey') public displayKey: string = '';
  @Input('taSuggestionTmpl') public suggestionTemplate: string = '';
  @Input('taClearOnSelect') public clearOnSelect: boolean = false;
  @Input('taDebounce') public debounce: number = 250;

  @Output('typeahead') public typeahead = new EventEmitter<any>();
  @Output('taSelected') public selected = new EventEmitter<any>();
  @Output('taEntered') public entered = new EventEmitter<any>();

  private itemSelected: boolean = false;
  private existingTimer: ng.IPromise<void> = null;

  constructor(@Inject('$element') private $element: ng.IAugmentedJQuery,
              @Inject('$compile') private $compile: ng.ICompileService,
              @Inject('$scope') private $scope: ng.IScope,
              @Inject('$templateRequest') private $templateRequest: ng.ITemplateRequestService,
              @Inject('$timeout') private $timeout: ng.ITimeoutService) {
  }

  @HostListener('keyup', ['$event'])
  public onKeyup(event: JQueryKeyEventObject): void {
    if (!this.itemSelected && event.keyCode == 13) {
      this.entered.emit({
        'value': $(this.$element).typeahead('val'),
        'callback': (reset: boolean) => {
          if (reset) {
            this.itemSelected = false;
            $(this.$element).typeahead('val', '');
          }
        }
      });
    }
  }

  public ngAfterContentInit(): void {
    var templates = null;
    if (this.suggestionTemplate) {
      templates = {};

      if (this.suggestionTemplate) {
        templates['suggestion'] = this.buildTemplateHandler(this.suggestionTemplate);
      }
    }

    $(this.$element).on('typeahead:select', (ev, suggestion) => {
      if (this.clearOnSelect) {
        $(this.$element).typeahead('val', '');
      }
      this.selected.emit({'result': suggestion});
      this.itemSelected = true;
    });

    $(this.$element).typeahead(
      {
        highlight: false,
        hint: false,
      },
      {
        templates: templates,
        display: this.displayKey,
        source: (query, results, asyncResults) => {
          this.debounceQuery(query, asyncResults);
        },
      });
  }

  private debounceQuery(query: string, asyncResults: Function): void {
    if (this.existingTimer) {
      this.$timeout.cancel(this.existingTimer);
      this.existingTimer = null;
    }

    this.existingTimer = this.$timeout(() => {
      this.typeahead.emit({'query': query, 'callback': asyncResults});
      this.itemSelected = false;
    }, this.debounce);
  }

  private buildTemplateHandler(templateUrl: string): Function {
    return (value) => {
      var resultDiv = document.createElement('div');
      this.$templateRequest(templateUrl).then((tplContent) => {
        var tplEl = document.createElement('span');
        tplEl.innerHTML = tplContent.trim();
        var scope = this.$scope.$new(true);
        scope['result'] = value;
        this.$compile(tplEl)(scope);
        resultDiv.appendChild(tplEl);
      });
      return resultDiv;
    };
  }
}
