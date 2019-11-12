import { RegexMatchViewComponent } from './regex-match-view.component';


describe("RegexMatchViewComponent", () => {
  var component: RegexMatchViewComponent;

  beforeEach(() => {
    component = new RegexMatchViewComponent();
  });

  describe("filterMatches", () => {
    var items: ({value: string})[];

    beforeEach(() => {
      items = [{value: "heads/master"}, {value: "heads/develop"}, {value: "heads/production"}];
    });

    it("returns null if given invalid regex expression", () => {
      var regexstr: string = "\\asfd\\";

      expect(component.filterMatches(regexstr, items, true)).toBe(null);
    });

    it("returns a subset of given items matching the given regex expression if given 'shouldMatch' as true", () => {
      var regexstr: string = `^${items[0].value}$`;
      var matches: ({value: string})[] = component.filterMatches(regexstr, items, true);

      expect(matches.length).toBeGreaterThan(0);
      matches.forEach((match) => {
        expect(items).toContain(match);
      });
    });

    it("returns a subset of given items not matching the given regex expression if given 'shouldMatch' as false", () => {
      var regexstr: string = `^${items[0].value}$`;
      var nonMatches: ({value: string})[] = component.filterMatches(regexstr, items, false);

      expect(nonMatches.length).toBeGreaterThan(0);
      nonMatches.forEach((nonMatch) => {
        expect(items).toContain(nonMatch);
      });
    });
  });
});
