import { Component, Input, Inject, Host, OnChanges, OnInit, SimpleChanges, HostListener } from 'ng-metadata/core';
import { LinearWorkflowComponent } from './linear-workflow.component';


/**
 * A component which displays a single section in a linear workflow.
 */
@Component({
  selector: 'linear-workflow-section',
  templateUrl: '/static/js/directives/ui/linear-workflow/linear-workflow-section.component.html',
  legacy: {
    transclude: true
  }
})
export class LinearWorkflowSectionComponent implements OnChanges, OnInit {

  @Input('@') public sectionId: string;
  @Input('@') public sectionTitle: string;
  @Input('<') public sectionValid: boolean = false;
  @Input('<') public skipSection: boolean = false;
  public sectionVisible: boolean = false;
  public isCurrentSection: boolean = false;

  constructor(@Host() @Inject(LinearWorkflowComponent) private parent: LinearWorkflowComponent) {

  }

  public ngOnInit(): void {
    if (!this.skipSection) {
      this.parent.addSection(this);
    }
  }

  public ngOnChanges(changes: SimpleChanges): void {
    switch (Object.keys(changes)[0]) {
      case 'sectionValid':
        if (changes['sectionValid'].previousValue && !changes['sectionValid'].currentValue && this.parent) {
          this.parent.onSectionInvalid(this.sectionId);
        }
        break;

      case 'skipSection':
        if (changes['skipSection'].currentValue && this.isCurrentSection && this.parent) {
          this.parent.onNextSection();
        }
        break;
    }
  }

  public onSubmitSection(): void {
    if (this.sectionValid) {
      this.parent.onNextSection();
    }
  }
}
