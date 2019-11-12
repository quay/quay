import { ClipboardCopyDirective } from './clipboard-copy.directive';
import * as Clipboard from 'clipboard';
import { Mock } from 'ts-mocks';
import Spy = jasmine.Spy;


describe("ClipboardCopyDirective", () => {
  var directive: ClipboardCopyDirective;
  var $elementMock: any;
  var $timeoutMock: any;
  var $documentMock: any;
  var clipboardFactory: any;
  var clipboardMock: Mock<Clipboard>;

  beforeEach(() => {
    $elementMock = new Mock<ng.IAugmentedJQuery>();
    $timeoutMock = jasmine.createSpy('$timeoutSpy').and.callFake((fn: () => void, delay) => fn());
    $documentMock = new Mock<ng.IDocumentService>();
    clipboardMock = new Mock<Clipboard>();
    clipboardMock.setup(mock => mock.on).is((eventName: string, callback: (event) => void) => {});
    clipboardFactory = jasmine.createSpy('clipboardFactory').and.returnValue(clipboardMock.Object);
    directive = new ClipboardCopyDirective(<any>[$elementMock.Object],
                                           $timeoutMock,
                                           <any>[$documentMock.Object],
                                           clipboardFactory);
    directive.copyTargetSelector = "#copy-input-box-0";
  });

  describe("ngAfterContentInit", () => {

    it("initializes new Clipboard instance", () => {
      const target = new Mock<ng.IAugmentedJQuery>();
      $documentMock.setup(mock => mock.querySelector).is(selector => target.Object);
      directive.ngAfterContentInit();

      expect(clipboardFactory).toHaveBeenCalled();
      expect((<Spy>clipboardFactory.calls.argsFor(0)[0])).toEqual($elementMock.Object);
      expect((<Spy>clipboardFactory.calls.argsFor(0)[1]['target']())).toEqual(target.Object);
    });

    it("sets error callback for Clipboard instance", () => {
      directive.ngAfterContentInit();

      expect((<Spy>clipboardMock.Object.on.calls.argsFor(0)[0])).toEqual('error');
      expect((<Spy>clipboardMock.Object.on.calls.argsFor(0)[1])).toBeDefined();
    });

    it("sets success callback for Clipboard instance", (done) => {
      directive.ngAfterContentInit();

      expect((<Spy>clipboardMock.Object.on.calls.argsFor(1)[0])).toEqual('success');
      expect((<Spy>clipboardMock.Object.on.calls.argsFor(1)[1])).toBeDefined();
      done();
    });
  });

  describe("ngOnDestroy", () => {

    beforeEach(() => {
      clipboardMock.setup(mock => mock.destroy).is(() => null);
    });

    it("calls method to destroy Clipboard instance if set", (done) => {
      directive.ngAfterContentInit();
      directive.ngOnDestroy();

      expect((<Spy>clipboardMock.Object.destroy)).toHaveBeenCalled();
      done();
    });

    it("does not call method to destroy Clipboard instance if not set", () => {
      directive.ngOnDestroy();

      expect((<Spy>clipboardMock.Object.destroy)).not.toHaveBeenCalled();
    });
  });
});