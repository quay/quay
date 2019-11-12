import { MarkdownViewComponent } from './markdown-view.component';
import { SimpleChanges } from 'ng-metadata/core';
import { Converter, ConverterOptions } from 'showdown';
import { Mock } from 'ts-mocks';
import Spy = jasmine.Spy;


describe("MarkdownViewComponent", () => {
  var component: MarkdownViewComponent;
  var markdownConverterMock: Mock<Converter>;
  var $sceMock: Mock<ng.ISCEService>;
  var $sanitizeMock: ng.sanitize.ISanitizeService;

  beforeEach(() => {
    markdownConverterMock = new Mock<Converter>();
    $sceMock = new Mock<ng.ISCEService>();
    $sanitizeMock = jasmine.createSpy('$sanitizeSpy').and.callFake((html: string) => html);
    component = new MarkdownViewComponent(markdownConverterMock.Object, $sceMock.Object, $sanitizeMock);
  });

  describe("ngOnChanges", () => {
    var changes: SimpleChanges;
    var markdown: string;
    var expectedPlaceholder: string;
    var markdownChars: string[];

    beforeEach(() => {
      changes = {};
      markdown = `## Heading\n    Code line\n\n- Item\n> Quote\`code snippet\`\n\nThis is my project!`;
      expectedPlaceholder = `<p style="visibility:hidden">placeholder</p>`;
      markdownChars = ['#', '-', '>', '`'];
      markdownConverterMock.setup(mock => mock.makeHtml).is((text) => text);
      $sceMock.setup(mock => mock.trustAsHtml).is((html) => html);
    });

    it("calls markdown converter to convert content to HTML when content is changed", () => {
      changes['content'] = {currentValue: markdown, previousValue: '', isFirstChange: () => false};
      component.ngOnChanges(changes);

      expect((<Spy>markdownConverterMock.Object.makeHtml).calls.argsFor(0)[0]).toEqual(changes['content'].currentValue);
    });

    it("only converts first line of content to HTML if flag is set when content is changed", () => {
      component.firstLineOnly = true;
      changes['content'] = {currentValue: markdown, previousValue: '', isFirstChange: () => false};
      component.ngOnChanges(changes);

      const expectedHtml: string = markdown.split('\n')
        .filter(line => line.indexOf('    ') != 0)
        .filter(line => line.trim().length != 0)
        .filter(line => markdownChars.indexOf(line.trim()[0]) == -1)[0];

      expect((<Spy>markdownConverterMock.Object.makeHtml).calls.argsFor(0)[0]).toEqual(expectedHtml);
    });

    it("sets converted HTML to be a placeholder if flag is set and content is empty", () => {
      component.placeholderNeeded = true;
      changes['content'] = {currentValue: '', previousValue: '', isFirstChange: () => false};
      component.ngOnChanges(changes);

      expect((<Spy>markdownConverterMock.Object.makeHtml)).not.toHaveBeenCalled();
      expect((<Spy>$sceMock.Object.trustAsHtml).calls.argsFor(0)[0]).toEqual(expectedPlaceholder);
    });

    it("sets converted HTML to empty string if placeholder flag is false and content is empty", () => {
      changes['content'] = {currentValue: '', previousValue: '', isFirstChange: () => false};
      component.ngOnChanges(changes);

      expect((<Spy>markdownConverterMock.Object.makeHtml).calls.argsFor(0)[0]).toEqual(changes['content'].currentValue);
    });

    it("calls $sanitize service to sanitize changed HTML content", () => {
      changes['content'] = {currentValue: markdown, previousValue: '', isFirstChange: () => false};
      component.ngOnChanges(changes);

      expect((<Spy>$sanitizeMock).calls.argsFor(0)[0]).toEqual(changes['content'].currentValue);
    });
  });
});
