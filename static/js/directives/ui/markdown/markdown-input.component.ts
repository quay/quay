import { Component, Input, Output, EventEmitter } from 'ng-metadata/core';
import './markdown-input.component.css';


/**
 * Displays editable Markdown content.
 */
@Component({
  selector: 'markdown-input',
  templateUrl: '/static/js/directives/ui/markdown/markdown-input.component.html'
})
export class MarkdownInputComponent {

  @Input('<') public content: string;
  @Input('<') public canWrite: boolean;
  @Input('@') public fieldTitle: string;

  @Output() public contentChanged: EventEmitter<{content: string}> = new EventEmitter();

  private isEditing: boolean = false;

  public editContent(): void {
    this.isEditing = true;
  }

  public saveContent(event: {editedContent: string}): void {
    this.contentChanged.emit({content: event.editedContent});
    this.isEditing = false;
  }

  public discardContent(event: any): void {
    this.isEditing = false;
  }
}
