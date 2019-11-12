import { MarkdownInputComponent } from './markdown-input.component';
import { Mock } from 'ts-mocks';
import Spy = jasmine.Spy;


describe("MarkdownInputComponent", () => {
  var component: MarkdownInputComponent;

  beforeEach(() => {
    component = new MarkdownInputComponent();
  });

  describe("editContent", () => {

  });

  describe("saveContent", () => {
    var editedContent: string;

    it("emits output event with changed content", (done) => {
      editedContent = "# Some markdown here";
      component.contentChanged.subscribe((event: {content: string}) => {
        expect(event.content).toEqual(editedContent);
        done();
      });

      component.saveContent({editedContent: editedContent});
    });
  });

  describe("discardContent", () => {

  });
});
