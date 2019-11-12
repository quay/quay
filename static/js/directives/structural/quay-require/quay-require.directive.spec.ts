import { QuayRequireDirective } from './quay-require.directive';
import { Mock } from 'ts-mocks';
import Spy = jasmine.Spy;


describe("QuayRequireDirective", () => {
  var directive: QuayRequireDirective;
  var featuresMock: Mock<any>;
  var $elementMock: Mock<ng.IAugmentedJQuery>;
  var $scopeMock: Mock<ng.IScope>;
  var $transcludeMock: Mock<ng.ITranscludeFunction>;
  var ngIfDirectiveMock: Mock<ng.IDirective>;

  beforeEach(() => {
    featuresMock = new Mock<any>();
    $elementMock = new Mock<ng.IAugmentedJQuery>();
    $scopeMock = new Mock<ng.IScope>();
    $transcludeMock = new Mock<ng.ITranscludeFunction>();
    ngIfDirectiveMock = new Mock<ng.IDirective>();

    directive = new QuayRequireDirective(featuresMock.Object,
                                         $elementMock.Object,
                                         $scopeMock.Object,
                                         $transcludeMock.Object,
                                         [ngIfDirectiveMock.Object]);
    directive.requiredFeatures = ['BILLING', 'SOME_OTHER_FEATURE'];
  });

  describe("ngAfterContentInit", () => {
    var linkMock: Mock<ng.IDirectiveLinkFn>;

    beforeEach(() => {
      linkMock = new Mock<ng.IDirectiveLinkFn>();
      linkMock.setup(mock => (<Function>mock).apply);
      ngIfDirectiveMock.setup(mock => mock.link).is(linkMock.Object);
    });

    it("calls ngIfDirective link method with own element's arguments to achieve ngIf functionality", () => {
      featuresMock.setup(mock => mock.matchesFeatures).is((features) => false);
      directive.ngAfterContentInit();

      expect((<Spy>(<Function>linkMock.Object).apply).calls.argsFor(0)[0]).toEqual(ngIfDirectiveMock.Object);
      expect((<Spy>(<Function>linkMock.Object).apply).calls.argsFor(0)[1][0]).toEqual($elementMock.Object);
      expect((<Spy>(<Function>linkMock.Object).apply).calls.argsFor(0)[1][1]).toEqual($scopeMock.Object);
      expect(Object.keys((<Spy>(<Function>linkMock.Object).apply).calls.argsFor(0)[1][2])).toEqual(['ngIf']);
      expect((<Spy>(<Function>linkMock.Object).apply).calls.argsFor(0)[1][3]).toEqual(null);
      expect((<Spy>(<Function>linkMock.Object).apply).calls.argsFor(0)[1][4]).toEqual($transcludeMock.Object);
    });

    it("calls feature service to check if given features are present in application", () => {
      featuresMock.setup(mock => mock.matchesFeatures).is((features) => false);
      directive.ngAfterContentInit();

      expect((<Spy>(<Function>linkMock.Object).apply).calls.argsFor(0)[1][2]['ngIf']()).toBe(false);
      expect(featuresMock.Object.matchesFeatures).toHaveBeenCalled();
      expect((<Spy>featuresMock.Object.matchesFeatures).calls.argsFor(0)[0]).toEqual(directive.requiredFeatures);
    });
  });
});
