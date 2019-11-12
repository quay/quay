import { RouteBuilderImpl } from './route-builder.service.impl';
import { PageService } from '../page/page.service';


describe("Service: RouteBuilderImpl", () => {
  var routeProviderMock: any;
  var pagesMock: any;
  var profiles: any[];

  beforeEach((() => {
    profiles = [
      {id: 'old-layout', templatePath: '/static/partials/'},
      {id: 'layout', templatePath: '/static/partials/'}
    ];
    routeProviderMock = jasmine.createSpyObj('routeProvider', ['otherwise', 'when']);
    pagesMock = jasmine.createSpyObj('pagesMock', ['get', 'create']);
  }));

  describe("constructor", () => {

    it("returns a RouteBuilder object", () => {
      var routeBuilder: RouteBuilderImpl = new RouteBuilderImpl(routeProviderMock, pagesMock);

      expect(routeBuilder).toBeDefined();
    });

    it("initializes current profile to 'layout'", () => {
      var routeBuilder: RouteBuilderImpl = new RouteBuilderImpl(routeProviderMock, pagesMock);

      expect(routeBuilder.currentProfile).toEqual('layout');
    });

    it("initializes available profiles", () => {
      var routeBuilder: RouteBuilderImpl = new RouteBuilderImpl(routeProviderMock, pagesMock);
      var matchingRoutes: any[] = routeBuilder.profiles.filter((profile) => {
        return profiles.indexOf(profile) == -1;
      });
      expect(matchingRoutes).toEqual(routeBuilder.profiles);
    });

    it("sets 'profiles' to the first given profile with id matching given current profile", () => {
      var routeBuilder: RouteBuilderImpl = new RouteBuilderImpl(routeProviderMock, pagesMock);

      expect(routeBuilder.profiles).toEqual([profiles[1]]);
    });
  });

  describe("otherwise", () => {
    var routeBuilder: RouteBuilderImpl;

    beforeEach(() => {
      routeBuilder = new RouteBuilderImpl(routeProviderMock, pagesMock);
    });

    it("calls routeProvider to set fallback route with given options", () => {
      var options = {1: "option"};
      routeBuilder.otherwise(options);

      expect(routeProviderMock.otherwise.calls.argsFor(0)[0]).toEqual(options);
    });
  });

  describe("route", () => {
    var routeBuilder: RouteBuilderImpl;
    var path: string;
    var pagename: string;
    var page: any;

    beforeEach(() => {
      path = '/repository/:namespace/:name';
      pagename = 'repo-view';
      page = {
        templateName: 'repository.html',
        reloadOnSearch: false,
        controller: jasmine.createSpy('pageController'),
        flags: {},
      };
      routeBuilder = new RouteBuilderImpl(routeProviderMock, pagesMock);
    });

    it("calls pages with given pagename and 'profiles' to get matching page and profile pair", () => {
      pagesMock.get.and.returnValue([profiles[1], page]);
      routeBuilder.route(path, pagename);

      expect(pagesMock.get.calls.argsFor(0)[0]).toEqual(pagename);
      expect(pagesMock.get.calls.argsFor(0)[1]).toEqual(routeBuilder.profiles);
    });

    it("throws error if no matching page/profile pair found", () => {
      pagesMock.get.and.returnValue();
      try {
        routeBuilder.route(path, pagename);
        fail();
      } catch (error) {
        expect(error.message).toEqual('Unknown page: ' + pagename);
      }
    });

    it("calls routeProvider to set route for given path and options", () => {
      pagesMock.get.and.returnValue([profiles[1], page]);
      var expectedOptions: any = {
        templateUrl: profiles[1].templatePath + page.templateName,
        reloadOnSearch: false,
        controller: page.controller,
      };
      routeBuilder.route(path, pagename);

      expect(routeProviderMock.when.calls.argsFor(0)[0]).toEqual(path);
      expect(routeProviderMock.when.calls.argsFor(0)[1]).toEqual(expectedOptions);
    });

    it("returns itself (the RouteBuilder instance)", () => {
      pagesMock.get.and.returnValue([profiles[1], page]);

      expect(routeBuilder.route(path, pagename)).toEqual(routeBuilder);
    });
  });
});