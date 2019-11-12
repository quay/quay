import { LinearWorkflowComponent, SectionInfo } from './linear-workflow.component';
import { LinearWorkflowSectionComponent } from './linear-workflow-section.component';
import Spy = jasmine.Spy;


describe("LinearWorkflowComponent", () => {
  var component: LinearWorkflowComponent;

  beforeEach(() => {
    component = new LinearWorkflowComponent();
  });

  describe("addSection", () => {
    var newSection: LinearWorkflowSectionComponent;

    beforeEach(() => {
      newSection = new LinearWorkflowSectionComponent(component);
    });

    it("sets 'sectionVisible' and 'isCurrentSection' to first section in list that is not skipped", () => {
      var skippedSection: LinearWorkflowSectionComponent = new LinearWorkflowSectionComponent(component);
      skippedSection.skipSection = true;
      component.addSection(skippedSection);
      component.addSection(newSection);

      expect(newSection.sectionVisible).toBe(true);
      expect(newSection.isCurrentSection).toBe(true);
    });
  });

  describe("onNextSection", () => {
    var currentSection: LinearWorkflowSectionComponent;

    beforeEach(() => {
      component.onWorkflowComplete = jasmine.createSpyObj("onWorkflowCompleteSpy", ['emit']);
      currentSection = new LinearWorkflowSectionComponent(component);
      currentSection.sectionValid = true;
      component.addSection(currentSection);
    });

    it("does not complete workflow or change current section if current section is invalid", () => {
      currentSection.sectionValid = false;
      component.onNextSection();

      expect(component.onWorkflowComplete.emit).not.toHaveBeenCalled();
      expect(currentSection.isCurrentSection).toBe(true);
    });

    it("calls workflow completed output callback if current section is the last section and is valid", () => {
      component.onNextSection();

      expect(component.onWorkflowComplete.emit).toHaveBeenCalled();
    });

    it("sets the current section to the next section if there are remaining sections and current section valid", () => {
      var nextSection: LinearWorkflowSectionComponent = new LinearWorkflowSectionComponent(component);
      component.addSection(nextSection);
      component.onNextSection();

      expect(currentSection.isCurrentSection).toBe(false);
      expect(nextSection.isCurrentSection).toBe(true);
      expect(nextSection.sectionVisible).toBe(true);
    });

    it("does not set the current section to a skipped section", () => {
      var skippedSection: LinearWorkflowSectionComponent = new LinearWorkflowSectionComponent(component);
      var nextSection: LinearWorkflowSectionComponent = new LinearWorkflowSectionComponent(component);
      skippedSection.skipSection = true;
      component.addSection(skippedSection);
      component.addSection(nextSection);
      component.onNextSection();

      expect(currentSection.isCurrentSection).toBe(false);
      expect(skippedSection.isCurrentSection).toBe(false);
      expect(skippedSection.sectionVisible).toBe(false);
      expect(nextSection.isCurrentSection).toBe(true);
      expect(nextSection.sectionVisible).toBe(true);
    });
  });

  describe("onSectionInvalid", () => {
    var invalidSection: LinearWorkflowSectionComponent;
    var sections: LinearWorkflowSectionComponent[];

    beforeEach(() => {
      invalidSection = new LinearWorkflowSectionComponent(component);
      invalidSection.sectionId = "Git Repository";
      invalidSection.sectionValid = false;
      component.addSection(invalidSection);

      sections = [
        new LinearWorkflowSectionComponent(component),
        new LinearWorkflowSectionComponent(component),
        new LinearWorkflowSectionComponent(component),
      ];
      sections.forEach((section) => {
        section.sectionVisible = false;
        section.isCurrentSection = false;
        component.addSection(section);
      });
    });

    it("does nothing if invalid section is after the current section", () => {
      sections[sections.length - 1].sectionValid = false;
      sections[sections.length - 1].sectionId = "Some Section";
      component.onSectionInvalid(sections[sections.length - 1].sectionId);

      expect(sections[sections.length - 1].isCurrentSection).toBe(false);
      expect(sections[sections.length - 1].sectionVisible).toBe(false);
    });

    it("sets the section with the given id to be the current section", () => {
      component.onSectionInvalid(invalidSection.sectionId);

      expect(invalidSection.isCurrentSection).toBe(true);
    });

    it("hides all sections after the section with the given id", () => {
      sections.forEach((section) => {
        section.sectionVisible = true;
        section.isCurrentSection = true;
        component.addSection(section);
      });
      component.onSectionInvalid(invalidSection.sectionId);

      sections.forEach((section) => {
        expect(section.sectionVisible).toBe(false);
        expect(section.isCurrentSection).toBe(false);
      });
    });
  });
});
