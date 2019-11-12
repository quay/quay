import { Component, Input, Inject, OnChanges, SimpleChanges } from 'ng-metadata/core';
import { Converter, ConverterOptions } from 'showdown';
import './markdown-view.component.css';


/**
 * Renders Markdown content to HTML.
 */
@Component({
  selector: 'markdown-view',
  templateUrl: '/static/js/directives/ui/markdown/markdown-view.component.html'
})
export class MarkdownViewComponent implements OnChanges {

  @Input('<') public content: string;
  @Input('<') public firstLineOnly: boolean = false;
  @Input('<') public placeholderNeeded: boolean = false;

  private convertedHTML: string = '';
  private readonly placeholder: string = `<p style="visibility:hidden">placeholder</p>`;
  private readonly markdownChars: string[] = ['#', '-', '>', '`'];

  constructor(@Inject('markdownConverter') private markdownConverter: Converter,
              @Inject('$sce') private $sce: ng.ISCEService,
              @Inject('$sanitize') private $sanitize: ng.sanitize.ISanitizeService) {

  }

  public ngOnChanges(changes: SimpleChanges): void {
    if (changes['content']) {
      if (!changes['content'].currentValue && this.placeholderNeeded) {
        this.convertedHTML = this.$sce.trustAsHtml(this.placeholder);
      } else if (this.firstLineOnly && changes['content'].currentValue) {
        const firstLine: string = changes['content'].currentValue.split('\n')
          // Skip code lines
          .filter(line => line.indexOf('    ') != 0)
          // Skip empty lines
          .filter(line => line.trim().length != 0)
          // Skip control lines
          .filter(line => this.markdownChars.indexOf(line.trim()[0]) == -1)[0];

        this.convertedHTML = this.$sanitize(this.markdownConverter.makeHtml(firstLine));
      } else {
        this.convertedHTML = this.$sanitize(this.markdownConverter.makeHtml(changes['content'].currentValue || ''));
      }
    }
  }
}
