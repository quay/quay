import { Input, Component, Inject } from 'ng-metadata/core';


/**
 * A component that displays a search box with autocomplete.
 */
@Component({
  selector: 'search-box',
  templateUrl: '/static/js/directives/ui/search-box/search-box.component.html',
})
export class SearchBoxComponent {
  @Input('<query') public enteredQuery: string = '';
  @Input('@clearOnSearch') public clearOnSearch: string = 'true';

  private isSearching: boolean = false;
  private currentQuery: string = '';
  private autocompleteSelected: boolean = false;

  constructor(@Inject('ApiService') private ApiService: any,
              @Inject('$timeout') private $timeout: ng.ITimeoutService,
              @Inject('$location') private $location: ng.ILocationService) {
  }

  private onTypeahead($event): void {
    this.currentQuery = $event['query'];
    if (this.currentQuery.length < 3) {
      $event['callback']([]);
      return;
    }

    var params = {
       'query': this.currentQuery,
    };

    this.ApiService.conductSearch(null, params).then((resp) => {
      if (this.currentQuery == $event['query']) {
        $event['callback'](resp.results);
        this.autocompleteSelected = false;
      }
    });
  }

  private onSelected($event): void {
    this.autocompleteSelected = true;
    this.$timeout(() => {
      this.$location.url($event['result']['href']);
    }, 100);
  }

  private onEntered($event): void {
    this.$timeout(() => {
      $event['callback'](this.clearOnSearch == 'true'); // Clear the value.
      this.$location.url('/search');
      this.$location.search('q', $event['value']);
    }, 10);
  }
}
