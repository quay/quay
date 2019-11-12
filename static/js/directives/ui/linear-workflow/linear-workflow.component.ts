import { Component, Output, Input, EventEmitter } from 'ng-metadata/core';
import { LinearWorkflowSectionComponent } from './linear-workflow-section.component';


/**
 * A component that which displays a linear workflow of sections, each completed in order before the next
 * step is made visible.
 */
@Component({
  selector: 'linear-workflow',
  templateUrl: '/static/js/directives/ui/linear-workflow/linear-workflow.component.html',
  legacy: {
    transclude: true
  }
})
export class LinearWorkflowComponent {

  @Input('@') public doneTitle: string;
  @Output() public onWorkflowComplete: EventEmitter<any> = new EventEmitter();
  private sections: SectionInfo[] = [];
  private currentSection: SectionInfo;

  public addSection(component: LinearWorkflowSectionComponent): void {
    this.sections.push({
      index: this.sections.length,
      component: component,
    });

    if (this.sections.length > 0 && !this.currentSection) {
      this.setNextSection(0);
    }
  }

  public onNextSection(): void {
    if (this.currentSection.component.sectionValid && this.currentSection.index + 1 >= this.sections.length) {
      this.onWorkflowComplete.emit({});
    }
    else if (this.currentSection.component.sectionValid && this.currentSection.index + 1 < this.sections.length) {
      this.currentSection.component.isCurrentSection = false;
      this.setNextSection(this.currentSection.index + 1);
    }
  }

  public onSectionInvalid(sectionId: string): void {
    var invalidSection = this.sections.filter(section => section.component.sectionId == sectionId)[0];
    if (invalidSection.index <= this.currentSection.index) {
      invalidSection.component.isCurrentSection = true;
      this.currentSection = invalidSection;

      this.sections.forEach((section) => {
        if (section.index > invalidSection.index) {
          section.component.sectionVisible = false;
          section.component.isCurrentSection = false;
        }
      });
    }
  }

  private setNextSection(startingIndex: number = 0): void {
    // Find the next section that is not set to be skipped
    this.currentSection = this.sections.slice(startingIndex)
      .filter(section => !section.component.skipSection)[0];

    if (this.currentSection) {
      this.currentSection.component.sectionVisible = true;
      this.currentSection.component.isCurrentSection = true;
    }
  }
}


/**
 * A type representing a section of the linear workflow.
 */
export type SectionInfo = {
  index: number;
  component: LinearWorkflowSectionComponent;
};
