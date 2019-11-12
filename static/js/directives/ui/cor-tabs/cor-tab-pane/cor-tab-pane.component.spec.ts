import { CorTabPaneComponent } from './cor-tab-pane.component';
import { CorTabPanelComponent } from '../cor-tab-panel/cor-tab-panel.component';
import { Mock } from 'ts-mocks';
import { BehaviorSubject } from 'rxjs/BehaviorSubject';
import Spy = jasmine.Spy;


describe("CorTabPaneComponent", () => {
  var component: CorTabPaneComponent;
  var panelMock: Mock<CorTabPanelComponent>;
  var activeTab: BehaviorSubject<string>;

  beforeEach(() => {
    activeTab = new BehaviorSubject<string>(null);
    spyOn(activeTab, "subscribe").and.callThrough();
    panelMock = new Mock<CorTabPanelComponent>();
    panelMock.setup(mock => mock.activeTab).is(activeTab);

    component = new CorTabPaneComponent(panelMock.Object);
    component.id = 'description';
  });

  describe("ngOnInit", () => {

    beforeEach(() => {
      panelMock.setup(mock => mock.addTabPane);
    });

    it("adds self as tab pane to panel", () => {
      component.ngOnInit();

      expect((<Spy>panelMock.Object.addTabPane).calls.argsFor(0)[0]).toBe(component);
    });

    it("subscribes to active tab changes", () => {
      component.ngOnInit();

      expect((<Spy>panelMock.Object.activeTab.subscribe)).toHaveBeenCalled();
    });

    it("does nothing if active tab ID is undefined", () => {
      component.ngOnInit();
      component.isActiveTab = true;
      panelMock.Object.activeTab.next(null);

      expect(component.isActiveTab).toEqual(true);
    });

    it("sets self as active if active tab ID matches tab ID", () => {
      component.ngOnInit();
      panelMock.Object.activeTab.next(component.id);

      expect(component.isActiveTab).toEqual(true);
    });

    it("sets self as inactive if active tab ID does not match tab ID", () => {
      component.ngOnInit();
      panelMock.Object.activeTab.next(component.id.split('').reverse().join(''));

      expect(component.isActiveTab).toEqual(false);
    });
  });
});
