import { CorTabPanelComponent } from './cor-tab-panel.component';
import { CorTabComponent } from '../cor-tab/cor-tab.component';
import { SimpleChanges } from 'ng-metadata/core';
import Spy = jasmine.Spy;


describe("CorTabPanelComponent", () => {
  var component: CorTabPanelComponent;

  beforeEach(() => {
    component = new CorTabPanelComponent();
  });

  describe("ngOnInit", () => {
    var tabs: CorTabComponent[] = [];

    beforeEach(() => {
      // Add tabs to panel
      tabs.push(new CorTabComponent(component));
      tabs[0].tabId = "info";
      tabs.forEach((tab) => component.addTab(tab));

      spyOn(component.activeTab, "subscribe").and.callThrough();
      spyOn(component.activeTab, "next").and.callThrough();
      spyOn(component.tabChange, "emit").and.returnValue(null);
    });

    it("subscribes to active tab changes", () => {
      component.ngOnInit();

      expect(<Spy>component.activeTab.subscribe).toHaveBeenCalled();
    });

    it("emits next active tab with tab ID of first registered tab if given tab ID is null", () => {
      component.ngOnInit();
      component.activeTab.next(null);

      expect((<Spy>component.activeTab.next).calls.argsFor(1)[0]).toEqual(tabs[0].tabId);
    });

    it("does not emit output event for tab change if tab ID is null", () => {
      component.ngOnInit();
      component.activeTab.next(null);

      expect((<Spy>component.tabChange.emit).calls.allArgs).not.toContain(null);
    });

    it("emits output event for tab change when tab ID is not null", () => {
      component.ngOnInit();
      const tabId: string = "description";
      component.activeTab.next(tabId);

      expect((<Spy>component.tabChange.emit).calls.argsFor(1)[0]).toEqual(tabId);
    });
  });

  describe("ngOnChanges", () => {
    var changes: SimpleChanges;
    var tabs: CorTabComponent[] = [];

    beforeEach(() => {
      // Add tabs to panel
      tabs.push(new CorTabComponent(component));
      tabs.forEach((tab) => component.addTab(tab));

      changes = {
        'selectedIndex': {
          currentValue: 0,
          previousValue: null,
          isFirstChange: () => false
        },
      };

      spyOn(component.activeTab, "next").and.returnValue(null);
    });

    it("emits next active tab if 'selectedIndex' input changes and is valid", () => {
      component.ngOnChanges(changes);

      expect((<Spy>component.activeTab.next).calls.argsFor(0)[0]).toEqual(tabs[changes['selectedIndex'].currentValue].tabId);
    });

    it("does nothing if 'selectedIndex' input changed to invalid value", () => {
      changes['selectedIndex'].currentValue = 100;
      component.ngOnChanges(changes);

      expect(<Spy>component.activeTab.next).not.toHaveBeenCalled();
    });
  });

  describe("addTab", () => {

    beforeEach(() => {
      spyOn(component.activeTab, "next").and.returnValue(null);
    });

    it("emits next active tab if it is not set", () => {
      const tab: CorTabComponent = new CorTabComponent(component);
      component.addTab(tab);

      expect((<Spy>component.activeTab.next).calls.argsFor(0)[0]).toEqual(tab.tabId);
    });

    it("does not emit next active tab if it is already set", () => {
      spyOn(component.activeTab, "getValue").and.returnValue("description");
      const tab: CorTabComponent = new CorTabComponent(component);
      component.addTab(tab);

      expect(<Spy>component.activeTab.next).not.toHaveBeenCalled();
    });
  });

  describe("addTabPane", () => {

  });

  describe("isVertical", () => {

    it("returns true if orientation is 'vertical'", () => {
      component.orientation = 'vertical';
      const isVertical: boolean = component.isVertical();

      expect(isVertical).toBe(true);
    });

    it("returns false if orientation is not 'vertical'", () => {
      const isVertical: boolean = component.isVertical();

      expect(isVertical).toBe(false);
    });
  });
});
