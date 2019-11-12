import { Input, Component } from 'ng-metadata/core';


/**
 * A component that displays the matches and non-matches for a regular expression against a set of
 * items.
 */
@Component({
  selector: 'regex-match-view',
  templateUrl: '/static/js/directives/ui/regex-match-view/regex-match-view.component.html'
})
export class RegexMatchViewComponent {

  // FIXME: Use one-way data binding
  @Input('=') private regex: string;
  @Input('=') private items: any[];

  public filterMatches(regexstr: string, items: ({value: string})[], shouldMatch: boolean): ({value: string})[] | null {
    regexstr = regexstr || '.+';

    try {
      var regex = new RegExp(regexstr);
    } catch (ex) {
      return null;
    }

    return items.filter(function(item) {
      var value: string = item.value;
      var m: RegExpMatchArray = value.match(regex);
      var matches: boolean = !!(m && m[0].length == value.length);
      return matches == shouldMatch;
    });
  }
}
