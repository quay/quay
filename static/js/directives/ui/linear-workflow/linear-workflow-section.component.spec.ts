import { LinearWorkflowSectionComponent } from './linear-workflow-section.component';
import { LinearWorkflowComponent } from './linear-workflow.component';
import { SimpleChanges } from 'ng-metadata/core';
import { Mock } from 'ts-mocks';
import Spy = jasmine.Spy;


describe("LinearWorkflowSectionComponent", () => {
  var component: LinearWorkflowSectionComponent;
  var parentMock: Mock<LinearWorkflowComponent>;

  beforeEach(() => {
    parentMock = new Mock<LinearWorkflowComponent>();
    component = new LinearWorkflowSectionComponent(parentMock.Object);
    component.sectionId = "mysection";
  });

  describe("ngOnInit", () => {

    it("calls parent component to add itself as a section", () => {
      parentMock.setup(mock => mock.addSection).is((section) => null);
      component.ngOnInit();

      expect((<Spy>parentMock.Object.addSection).calls.argsFor(0)[0]).toBe(component);
    });
  });

  describe("ngOnChanges", () => {
    var changesObj: SimpleChanges;

    beforeEach(() => {
      parentMock.setup(mock => mock.onSectionInvalid).is((section) => null);
      changesObj = {
        sectionValid: {
          currentValue: true,
          previousValue: false,
          isFirstChange: () => false,
        },
        skipSection: {
          currentValue: true,
          previousValue: false,
          isFirstChange: () => false,
        },
      };
    });

    it("does nothing if 'sectionValid' input not changed", () => {
      component.ngOnChanges({});

      expect((<Spy>parentMock.Object.onSectionInvalid)).not.toHaveBeenCalled();
    });

    it("does nothing if 'sectionValid' input's previous value is falsy", () => {
      changesObj['sectionValid'].previousValue = null;
      component.ngOnChanges(changesObj);

      expect((<Spy>parentMock.Object.onSectionInvalid)).not.toHaveBeenCalled();
    });

    it("does nothing if 'sectionValid' input is true", () => {
      component.ngOnChanges(changesObj);

      expect((<Spy>parentMock.Object.onSectionInvalid)).not.toHaveBeenCalled();
    });

    it("calls parent method to inform that section is invalid if 'sectionValid' input changed to false", () => {
      changesObj['sectionValid'].previousValue = true;
      changesObj['sectionValid'].currentValue = false;
      component.ngOnChanges(changesObj);

      expect((<Spy>parentMock.Object.onSectionInvalid).calls.argsFor(0)[0]).toEqual(component.sectionId);
    });

    it("calls parent method to go to next section if 'skipSection' input is true and is current section", () => {
      delete changesObj['sectionValid'];
      parentMock.setup(mock => mock.onNextSection).is(() => null);
      component.isCurrentSection = true;
      component.ngOnChanges(changesObj);

      expect(<Spy>parentMock.Object.onNextSection).toHaveBeenCalled();
    });
  });

  describe("onSubmitSection", () => {

    beforeEach(() => {
      parentMock.setup(mock => mock.onNextSection).is(() => null);
    });

    it("does nothing if section is invalid", () => {
      component.sectionValid = false;
      component.onSubmitSection();

      expect(<Spy>parentMock.Object.onNextSection).not.toHaveBeenCalled();
    });

    it("calls parent method to go to next section if section is valid", () => {
      component.sectionValid = true;
      component.onSubmitSection();

      expect(<Spy>parentMock.Object.onNextSection).toHaveBeenCalled();
    });
  });
});
