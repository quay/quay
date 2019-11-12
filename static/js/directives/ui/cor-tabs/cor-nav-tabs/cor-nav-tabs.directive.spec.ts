import { CorNavTabsDirective } from './cor-nav-tabs.directive';
import { CorTabPanelComponent } from '../cor-tab-panel/cor-tab-panel.component';
import { Mock } from 'ts-mocks';
import { BehaviorSubject } from 'rxjs/BehaviorSubject';
import Spy = jasmine.Spy;


describe("CorNavTabsDirective", () => {
  var directive: CorNavTabsDirective;
  var panelMock: Mock<CorTabPanelComponent>;
  var $locationMock: Mock<ng.ILocationService>;
  var $rootScopeMock: Mock<ng.IRootScopeService>;
  var activeTab: BehaviorSubject<string>;
  const tabId: string = "description";

  beforeEach(() => {
    activeTab = new BehaviorSubject<string>(null);
    spyOn(activeTab, "next").and.returnValue(null);
    panelMock = new Mock<CorTabPanelComponent>();
    panelMock.setup(mock => mock.activeTab).is(activeTab);
    $locationMock = new Mock<ng.ILocationService>();
    $locationMock.setup(mock => mock.search).is(() => <any>{tab: tabId});
    $rootScopeMock = new Mock<ng.IRootScopeService>();
    $rootScopeMock.setup(mock => mock.$on);

    directive = new CorNavTabsDirective(panelMock.Object, $locationMock.Object, $rootScopeMock.Object);
  });

  describe("constructor", () => {

    it("subscribes to $routeUpdate event on the root scope", () => {
      expect((<Spy>$rootScopeMock.Object.$on).calls.argsFor(0)[0]).toEqual("$routeUpdate");
    });

    it("calls location service to retrieve tab id from URL query parameters on route update", () => {
      (<Spy>$rootScopeMock.Object.$on).calls.argsFor(0)[1]();

      expect(<Spy>$locationMock.Object.search).toHaveBeenCalled();
    });

    it("emits retrieved tab id as next active tab on route update", () => {
      (<Spy>$rootScopeMock.Object.$on).calls.argsFor(0)[1]();

      expect((<Spy>activeTab.next).calls.argsFor(0)[0]).toEqual(tabId);
    });
  });

  describe("ngAfterContentInit", () => {
    const path: string = "quay.io/repository/devtable/simple";

    beforeEach(() => {
      $locationMock.setup(mock => mock.path).is(() => <any>path);
    });

    it("calls location service to retrieve the current URL path and sets panel's base path", () => {
      directive.ngAfterContentInit();

      expect(panelMock.Object.basePath).toEqual(path);
    });

    it("calls location service to retrieve tab id from URL query parameters", () => {
      directive.ngAfterContentInit();

      expect(<Spy>$locationMock.Object.search).toHaveBeenCalled();
    });

    it("emits retrieved tab id as next active tab", () => {
      directive.ngAfterContentInit();

      expect((<Spy>activeTab.next).calls.argsFor(0)[0]).toEqual(tabId);
    });
  });
});
