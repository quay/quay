import { MarkdownEditorComponent, EditMode } from './markdown-editor.component';
import { MarkdownSymbol } from '../../../types/common.types';
import { Mock } from 'ts-mocks';
import Spy = jasmine.Spy;


describe("MarkdownEditorComponent", () => {
  var component: MarkdownEditorComponent;
  var textarea: Mock<ng.IAugmentedJQuery | any>;
  var documentMock: Mock<HTMLElement & Document>;
  var $windowMock: Mock<ng.IWindowService>;

  beforeEach(() => {
    textarea = new Mock<ng.IAugmentedJQuery | any>();
    documentMock = new Mock<HTMLElement & Document>();
    $windowMock = new Mock<ng.IWindowService>();
    const $documentMock: any = [documentMock.Object];
    component = new MarkdownEditorComponent($documentMock, $windowMock.Object, 'chrome');
    component.textarea = textarea.Object;
  });

  describe("onBeforeUnload", () => {

    it("returns false to alert user about losing current changes", () => {
      component.changeEditMode("write");
      const allow: boolean = component.onBeforeUnload();

      expect(allow).toBe(false);
    });
  });

  describe("ngOnDestroy", () => {

    it("removes 'beforeunload' event listener", () => {
      $windowMock.setup(mock => mock.onbeforeunload).is(() => 1);
      component.ngOnDestroy();

      expect($windowMock.Object.onbeforeunload.call(this)).toEqual(null);
    });
  });

  describe("changeEditMode", () => {

    it("sets component's edit mode to given mode", () => {
      const editMode: EditMode = "preview";
      component.changeEditMode(editMode);

      expect(component.currentEditMode).toEqual(editMode);
    });
  });

  describe("insertSymbol", () => {
    var event: {symbol: MarkdownSymbol};
    var markdownSymbols: {type: MarkdownSymbol, characters: string, shiftBy: number}[];
    var innerText: string;

    beforeEach(() => {
      event = {symbol: 'heading1'};
      innerText = "Here is some text";
      markdownSymbols = [
        {type: 'heading1',      characters: '# ',      shiftBy: 2},
        {type: 'heading2',      characters: '## ',     shiftBy: 3},
        {type: 'heading3',      characters: '### ',    shiftBy: 4},
        {type: 'bold',          characters: '****',    shiftBy: 2},
        {type: 'italics',       characters: '__',      shiftBy: 1},
        {type: 'bulleted-list', characters: '- ',      shiftBy: 2},
        {type: 'numbered-list', characters: '1. ',     shiftBy: 3},
        {type: 'quote',         characters: '> ',      shiftBy: 2},
        {type: 'link',          characters: '[](url)', shiftBy: 1},
        {type: 'code',          characters: '``',      shiftBy: 1},
      ];

      textarea.setup(mock => mock.focus);
      textarea.setup(mock => mock.substr).is((start, end) => '');
      textarea.setup(mock => mock.val).is((value?) => innerText);
      textarea.setup(mock => mock.prop).is((prop) => {
        switch (prop) {
          case "selectionStart":
            return 0;
          case "selectionEnd":
            return 0;
        }
      });
      documentMock.setup(mock => mock.execCommand).is((commandID, showUI, value) => false);
    });

    it("focuses on markdown textarea", () => {
      component.insertSymbol(event);

      expect(<Spy>textarea.Object.focus).toHaveBeenCalled();
    });

    it("inserts correct characters for given symbol at cursor position", () => {
      markdownSymbols.forEach((symbol) => {
        event.symbol = symbol.type;
        component.insertSymbol(event);

        expect((<Spy>documentMock.Object.execCommand).calls.argsFor(0)[0]).toEqual('insertText');
        expect((<Spy>documentMock.Object.execCommand).calls.argsFor(0)[1]).toBe(false);
        expect((<Spy>documentMock.Object.execCommand).calls.argsFor(0)[2]).toEqual(symbol.characters);

        (<Spy>documentMock.Object.execCommand).calls.reset();
      });
    });

    it("splices highlighted selection between inserted characters instead of deleting them", () => {
      markdownSymbols.slice(0, 1).forEach((symbol) => {
        textarea.setup(mock => mock.prop).is((prop) => {
          switch (prop) {
            case "selectionStart":
              return 0;
            case "selectionEnd":
              return innerText.length;
          }
        });
        event.symbol = symbol.type;
        component.insertSymbol(event);

        expect((<Spy>documentMock.Object.execCommand).calls.argsFor(0)[0]).toEqual('insertText');
        expect((<Spy>documentMock.Object.execCommand).calls.argsFor(0)[1]).toBe(false);
        expect((<Spy>documentMock.Object.execCommand).calls.argsFor(0)[2]).toEqual(`${symbol.characters.slice(0, symbol.shiftBy)}${innerText}${symbol.characters.slice(symbol.shiftBy, symbol.characters.length)}`);

        (<Spy>documentMock.Object.execCommand).calls.reset();
      });
    });

    it("moves cursor to correct position for given symbol", () => {
      markdownSymbols.forEach((symbol) => {
        event.symbol = symbol.type;
        component.insertSymbol(event);

        expect((<Spy>textarea.Object.prop).calls.argsFor(2)[0]).toEqual('selectionStart');
        expect((<Spy>textarea.Object.prop).calls.argsFor(2)[1]).toEqual(symbol.shiftBy);
        expect((<Spy>textarea.Object.prop).calls.argsFor(3)[0]).toEqual('selectionEnd');
        expect((<Spy>textarea.Object.prop).calls.argsFor(3)[1]).toEqual(symbol.shiftBy);

        (<Spy>textarea.Object.prop).calls.reset();
      });
    });
  });

  describe("saveChanges", () => {

    beforeEach(() => {
      component.content = "# Some markdown content";
    });

    it("emits output event with changed content", (done) => {
      component.save.subscribe((event: {editedContent: string}) => {
        expect(event.editedContent).toEqual(component.content);
        done();
      });

      component.saveChanges();
    });
  });

  describe("discardChanges", () => {

    it("prompts user to confirm discarding changes", () => {
      const confirmSpy: Spy = $windowMock.setup(mock => mock.confirm).is((message) => false).Spy;
      component.discardChanges();

      expect(confirmSpy.calls.argsFor(0)[0]).toEqual(`Are you sure you want to discard your changes?`);
    });

    it("emits output event with no content if user confirms discarding changes", (done) => {
      $windowMock.setup(mock => mock.confirm).is((message) => true);
      component.discard.subscribe((event: {}) => {
        expect(event).toEqual({});
        done();
      });

      component.discardChanges();
    });

    it("does not emit output event if user declines confirmation of discarding changes", (done) => {
      $windowMock.setup(mock => mock.confirm).is((message) => false);
      component.discard.subscribe((event: {}) => {
        fail(`Should not emit output event`);
        done();
      });

      component.discardChanges();
      done();
    });
  });
});
