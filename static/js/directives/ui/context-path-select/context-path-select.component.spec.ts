import { ContextPathSelectComponent, ContextChangeEvent } from './context-path-select.component';


describe("ContextPathSelectComponent", () => {
  var component: ContextPathSelectComponent;
  var currentContext: string;
  var isValidContext: boolean;
  var contexts: string[];

  beforeEach(() => {
    component = new ContextPathSelectComponent();
    currentContext = '/';
    isValidContext = false;
    contexts = ['/'];
    component.currentContext = currentContext;
    component.isValidContext = isValidContext;
    component.contexts = contexts;
  });

  describe("ngOnChanges", () => {

    it("sets valid context flag to true if current context is valid", () => {
      component.ngOnChanges({});

      expect(component.isValidContext).toBe(true);
    });

    it("sets valid context flag to false if current context is invalid", () => {
      component.currentContext = "asdfdsf";
      component.ngOnChanges({});

      expect(component.isValidContext).toBe(false);
    });
  });

  describe("setContext", () => {
    var newContext: string;

    beforeEach(() => {
      newContext = '/conf';
    });

    it("sets current context to given context", () => {
      component.setContext(newContext);

      expect(component.currentContext).toEqual(newContext);
    });

    it("sets valid context flag to true if given context is valid", () => {
      component.setContext(newContext);

      expect(component.isValidContext).toBe(true);
    });

    it("sets valid context flag to false if given context is invalid", () => {
      component.setContext("asdfsadfs");

      expect(component.isValidContext).toBe(false);
    });

    it("emits output event indicating build context changed", (done) => {
      component.contextChanged.subscribe((event: ContextChangeEvent) => {
        expect(event.contextDir).toEqual(newContext);
        expect(event.isValid).toEqual(component.isValidContext);
        done();
      });

      component.setContext(newContext);
    });
  });

  describe("setSelectedContext", () => {
    var newContext: string;

    beforeEach(() => {
      newContext = '/conf';
    });

    it("sets current context to given context", () => {
      component.setSelectedContext(newContext);

      expect(component.currentContext).toEqual(newContext);
    });

    it("sets valid context flag to true if given context is valid", () => {
      component.setSelectedContext(newContext);

      expect(component.isValidContext).toBe(true);
    });

    it("sets valid context flag to false if given context is invalid", () => {
      component.setSelectedContext("a;lskjdf;ldsa");

      expect(component.isValidContext).toBe(false);
    });

    it("emits output event indicating build context changed", (done) => {
      component.contextChanged.subscribe((event: ContextChangeEvent) => {
        expect(event.contextDir).toEqual(newContext);
        expect(event.isValid).toEqual(component.isValidContext);
        done();
      });

      component.setSelectedContext(newContext);
    });
  });
});