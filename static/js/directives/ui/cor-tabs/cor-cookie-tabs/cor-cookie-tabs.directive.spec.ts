import { CorCookieTabsDirective } from './cor-cookie-tabs.directive';
import { CorTabPanelComponent } from '../cor-tab-panel/cor-tab-panel.component';
import { Mock } from 'ts-mocks';
import { BehaviorSubject } from 'rxjs/BehaviorSubject';
import Spy = jasmine.Spy;


describe("CorCookieTabsDirective", () => {
  var directive: CorCookieTabsDirective;
  var panelMock: Mock<CorTabPanelComponent>;
  var cookieServiceMock: Mock<any>;
  var activeTab: BehaviorSubject<string>;

  beforeEach(() => {
    activeTab = new BehaviorSubject<string>(null);
    spyOn(activeTab, "subscribe").and.returnValue(null);
    panelMock = new Mock<CorTabPanelComponent>();
    panelMock.setup(mock => mock.activeTab).is(activeTab);
    cookieServiceMock = new Mock<any>();
    cookieServiceMock.setup(mock => mock.putPermanent).is((cookieName, value) => null);

    directive = new CorCookieTabsDirective(panelMock.Object, cookieServiceMock.Object);
    directive.cookieName = "quay.credentialsTab";
  });

  describe("ngAfterContentInit", () => {
    const tabId: string = "description";

    beforeEach(() => {
      cookieServiceMock.setup(mock => mock.get).is((name) => tabId);
      spyOn(activeTab, "next").and.returnValue(null);
    });

    it("calls cookie service to retrieve initial tab id", () => {
      directive.ngAfterContentInit();

      expect((<Spy>cookieServiceMock.Object.get).calls.argsFor(0)[0]).toEqual(directive.cookieName);
    });

    it("emits retrieved tab id as next active tab", () => {
      directive.ngAfterContentInit();

      expect((<Spy>panelMock.Object.activeTab.next).calls.argsFor(0)[0]).toEqual(tabId);
    });

    it("subscribes to active tab changes", () => {
      directive.ngAfterContentInit();

      expect((<Spy>panelMock.Object.activeTab.subscribe)).toHaveBeenCalled();
    });

    it("calls cookie service to put new permanent cookie on active tab changes", () => {
      directive.ngAfterContentInit();
      const tabId: string = "description";
      (<Spy>panelMock.Object.activeTab.subscribe).calls.argsFor(0)[0](tabId);

      expect((<Spy>cookieServiceMock.Object.putPermanent).calls.argsFor(0)[0]).toEqual(directive.cookieName);
      expect((<Spy>cookieServiceMock.Object.putPermanent).calls.argsFor(0)[1]).toEqual(tabId);
    });
  });
});
