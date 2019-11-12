import { ViewArrayImpl } from './view-array.impl';


describe("ViewArrayImplImpl", () => {
  var viewArrayImpl: ViewArrayImpl;
  var $intervalMock: any;

  beforeEach(() => {
    $intervalMock = jasmine.createSpy('$intervalSpy');
    $intervalMock.and.returnValue({});
    $intervalMock.cancel = jasmine.createSpy('cancelSpy');
    viewArrayImpl = new ViewArrayImpl($intervalMock);
  });


  describe("constructor", () => {

    it("initializes values", () => {
      expect(viewArrayImpl.isVisible).toBe(false);
      expect(viewArrayImpl.visibleEntries).toBe(null);
      expect(viewArrayImpl.entries.length).toEqual(0);
      expect(viewArrayImpl.hasEntries).toBe(false);
      expect(viewArrayImpl.hasHiddenEntries).toBe(false);
    });
  });

  describe("length", () => {

    it("returns the number of entries", () => {
      viewArrayImpl.entries = [{}, {}, {}];

      expect(viewArrayImpl.length()).toEqual(viewArrayImpl.entries.length);
    });
  });

  describe("get", () => {

    it("returns the entry at a given index", () => {
      var index: number = 8;
      viewArrayImpl.entries = new Array(10);
      viewArrayImpl.entries[index] = 3;

      expect(viewArrayImpl.get(index)).toEqual(viewArrayImpl.entries[index]);
    });
  });

  describe("push", () => {

    it("adds given element to the end of entries", () => {
      var element: number = 3;
      var originalLength: number = viewArrayImpl.length();
      viewArrayImpl.push(element);

      expect(viewArrayImpl.entries.length).toEqual(originalLength + 1);
      expect(viewArrayImpl.get(originalLength)).toEqual(element);
    });

    it("sets 'hasEntries' to true", () => {
      viewArrayImpl.push(2);

      expect(viewArrayImpl.hasEntries).toBe(true);
    });

    it("starts timer if 'isVisible' is true", () => {
      viewArrayImpl.isVisible = true;
      viewArrayImpl.push(2);

      expect($intervalMock).toHaveBeenCalled();
    });

    it("does not start timer if 'isVisible' is false", () => {
      viewArrayImpl.isVisible = false;
      viewArrayImpl.push(2);

      expect($intervalMock).not.toHaveBeenCalled();
    });
  });

  describe("toggle", () => {

    it("sets 'isVisible' to false if currently true", () => {
      viewArrayImpl.isVisible = true;
      viewArrayImpl.toggle();

      expect(viewArrayImpl.isVisible).toBe(false);
    });

    it("sets 'isVisible' to true if currently false", () => {
      viewArrayImpl.isVisible = false;
      viewArrayImpl.toggle();

      expect(viewArrayImpl.isVisible).toBe(true);
    });
  });

  describe("setVisible", () => {

    it("sets 'isVisible' to false if given false", () => {
      viewArrayImpl.setVisible(false);

      expect(viewArrayImpl.isVisible).toBe(false);
    });

    it("sets 'visibleEntries' to empty array if given false", () => {
      viewArrayImpl.setVisible(false);

      expect(viewArrayImpl.visibleEntries.length).toEqual(0);
    });

    it("shows additional entries if given true", () => {
      viewArrayImpl.setVisible(true);
    });

    it("does not show additional entries if given false", () => {
      viewArrayImpl.setVisible(false);
    });

    it("starts timer if given true", () => {
      viewArrayImpl.setVisible(true);

      expect($intervalMock).toHaveBeenCalled();
    });

    it("does not stop timer if given false and timer is not active", () => {
      viewArrayImpl.setVisible(false);

      expect($intervalMock.cancel).not.toHaveBeenCalled();
    });

    it("stops timer if given false and timer is active", () => {
      viewArrayImpl.isVisible = true;
      viewArrayImpl.push(2);
      viewArrayImpl.setVisible(false);

      expect($intervalMock.cancel).toHaveBeenCalled();
    });
  });

  describe("create", () => {

    it("returns a new ViewArrayImpl instance", () => {
      var newViewArrayImpl: ViewArrayImpl = viewArrayImpl.create();

      expect(newViewArrayImpl).toBeDefined();
    });
  });
});