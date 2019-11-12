import { CorTabComponent } from './cor-tab.component';
import { CorTabPanelComponent } from '../cor-tab-panel/cor-tab-panel.component';
import { Mock } from 'ts-mocks';
import { BehaviorSubject } from 'rxjs/BehaviorSubject';
import Spy = jasmine.Spy;


describe("CorTabComponent", () => {
  var component: CorTabComponent;
  var panelMock: Mock<CorTabPanelComponent>;
  var activeTab: BehaviorSubject<string>;

  beforeEach(() => {
    activeTab = new BehaviorSubject<string>(null);
    spyOn(activeTab, "subscribe").and.callThrough();
    panelMock = new Mock<CorTabPanelComponent>();
    panelMock.setup(mock => mock.activeTab).is(activeTab);

    component = new CorTabComponent(panelMock.Object);
  });

  describe("ngOnInit", () => {

    beforeEach(() => {
      panelMock.setup(mock => mock.addTab);
      spyOn(component.tabInit, "emit").and.returnValue(null);
      spyOn(component.tabShow, "emit").and.returnValue(null);
      spyOn(component.tabHide, "emit").and.returnValue(null);
      component.tabId = "description";
    });

    it("subscribes to active tab changes", () => {
      component.ngOnInit();

      expect((<Spy>panelMock.Object.activeTab.subscribe)).toHaveBeenCalled();
    });

    it("does nothing if active tab ID is undefined", () => {
      component.ngOnInit();
      panelMock.Object.activeTab.next(null);

      expect(<Spy>component.tabInit.emit).not.toHaveBeenCalled();
      expect(<Spy>component.tabShow.emit).not.toHaveBeenCalled();
      expect(<Spy>component.tabHide.emit).not.toHaveBeenCalled();
    });

    it("emits output event for tab init if it is new active tab", () => {
      component.ngOnInit();
      panelMock.Object.activeTab.next(component.tabId);

      expect(<Spy>component.tabInit.emit).toHaveBeenCalled();
    });

    it("emits output event for tab show if it is new active tab", () => {
      component.ngOnInit();
      panelMock.Object.activeTab.next(component.tabId);

      expect(<Spy>component.tabShow.emit).toHaveBeenCalled();
    });

    it("emits output event for tab hide if active tab changes to different tab", () => {
      const newTabId: string = component.tabId.split('').reverse().join('');
      component.ngOnInit();
      // Call twice, first time to set 'isActive' to true
      panelMock.Object.activeTab.next(component.tabId);
      panelMock.Object.activeTab.next(newTabId);

      expect(<Spy>component.tabHide.emit).toHaveBeenCalled();
    });

    it("does not emit output event for tab hide if was not previously active tab", () => {
      const newTabId: string = component.tabId.split('').reverse().join('');
      component.ngOnInit();
      panelMock.Object.activeTab.next(newTabId);

      expect(<Spy>component.tabHide.emit).not.toHaveBeenCalled();
    });

    it("adds self as tab to panel", () => {
      component.ngOnInit();

      expect((<Spy>panelMock.Object.addTab).calls.argsFor(0)[0]).toBe(component);
    });
  });
});
