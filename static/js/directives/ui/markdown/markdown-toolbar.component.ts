import { Component, Input, Output, EventEmitter } from 'ng-metadata/core';
import { MarkdownSymbol } from '../../../types/common.types';
import './markdown-toolbar.component.css';


/**
 * Toolbar containing Markdown symbol shortcuts.
 */
@Component({
  selector: 'markdown-toolbar',
  templateUrl: '/static/js/directives/ui/markdown/markdown-toolbar.component.html'
})
export class MarkdownToolbarComponent {

  @Input('<') public allowUndo: boolean = true;
  @Output() public insertSymbol: EventEmitter<{symbol: MarkdownSymbol}> = new EventEmitter();
}
