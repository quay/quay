import { Component, Inject, Input, Output, EventEmitter, ViewChild, HostListener, OnDestroy } from 'ng-metadata/core';
import { MarkdownSymbol } from '../../../types/common.types';
import { BrowserPlatform } from '../../../constants/platform.constant';
import './markdown-editor.component.css';


/**
 * An editing interface for Markdown content.
 */
@Component({
  selector: 'markdown-editor',
  templateUrl: '/static/js/directives/ui/markdown/markdown-editor.component.html'
})
export class MarkdownEditorComponent implements OnDestroy {

  @Input('<') public content: string;

  @Output() public save: EventEmitter<{editedContent: string}> = new EventEmitter();
  @Output() public discard: EventEmitter<any> = new EventEmitter();

  // Textarea is public for testability, should not be directly accessed
  @ViewChild('#markdown-textarea') public textarea: ng.IAugmentedJQuery;

  private editMode: EditMode = "write";

  constructor(@Inject('$document') private $document: ng.IDocumentService,
              @Inject('$window') private $window: ng.IWindowService,
              @Inject('BrowserPlatform') private browserPlatform: BrowserPlatform) {
    this.$window.onbeforeunload = this.onBeforeUnload.bind(this);
  }

  @HostListener('window:beforeunload', [])
  public onBeforeUnload(): boolean {
    return false;
  }

  public ngOnDestroy(): void {
    this.$window.onbeforeunload = () => null;
  }

  public changeEditMode(newMode: EditMode): void {
    this.editMode = newMode;
  }

  public insertSymbol(event: {symbol: MarkdownSymbol}): void {
    this.textarea.focus();

    const startPos: number = this.textarea.prop('selectionStart');
    const endPos: number = this.textarea.prop('selectionEnd');
    const innerText: string = this.textarea.val().slice(startPos, endPos);
    var shiftBy: number = 0;
    var characters: string = '';

    switch (event.symbol) {
      case 'heading1':
        characters = '# ';
        shiftBy = 2;
        break;
      case 'heading2':
        characters = '## ';
        shiftBy = 3;
        break;
      case 'heading3':
        characters = '### ';
        shiftBy = 4;
        break;
      case 'bold':
        characters = '****';
        shiftBy = 2;
        break;
      case 'italics':
        characters = '__';
        shiftBy = 1;
        break;
      case 'bulleted-list':
        characters = '- ';
        shiftBy = 2;
        break;
      case 'numbered-list':
        characters = '1. ';
        shiftBy = 3;
        break;
      case 'quote':
        characters = '> ';
        shiftBy = 2;
        break;
      case 'link':
        characters = '[](url)';
        shiftBy = 1;
        break;
      case 'code':
        characters = '``';
        shiftBy = 1;
        break;
    }

    const cursorPos: number = startPos + shiftBy;

    if (startPos != endPos) {
      this.insertText(`${characters.slice(0, shiftBy)}${innerText}${characters.slice(shiftBy, characters.length)}`,
                      startPos,
                      endPos);
    }
    else {
      this.insertText(characters, startPos, endPos);
    }

    this.textarea.prop('selectionStart', cursorPos);
    this.textarea.prop('selectionEnd', cursorPos);
  }

  public saveChanges(): void {
    this.save.emit({editedContent: this.content});
  }

  public discardChanges(): void {
    if (this.$window.confirm(`Are you sure you want to discard your changes?`)) {
      this.discard.emit({});
    }
  }

  public get currentEditMode(): EditMode {
    return this.editMode;
  }

  /**
   * Insert text in such a way that the browser adds it to the 'undo' stack. This has different feature support
   * depending on the platform.
   */
  private insertText(text: string, startPos: number, endPos: number): void {
    if (this.browserPlatform === 'firefox') {
      // FIXME: Ctrl-Z highlights previous text
      this.textarea.val(<string>this.textarea.val().substr(0, startPos) +
                        text +
                        <string>this.textarea.val().substr(endPos, this.textarea.val().length));
    }
    else {
      // TODO: Test other platforms (IE...)
      this.$document[0].execCommand('insertText', false, text);
    }
  }
}


/**
 * Type representing the current editing mode.
 */
export type EditMode = "write" | "preview";
