import { NgModule } from 'ng-metadata/core';
import { Converter } from 'showdown';
import * as showdown from 'showdown';
import { registerLanguage, highlightAuto } from 'highlight.js/lib/highlight';
import 'highlight.js/styles/vs.css';
const highlightedLanguages: string[] = require('../../../constants/highlighted-languages.constant.json');

/**
 * Dynamically fetch and register a new language with Highlight.js
 */
export const addHighlightedLanguage = (language: string): Promise<{}> => {
  return new Promise(async(resolve, reject) => {
    try {
      const langModule = await System.import(`highlight.js/lib/languages/${language}`);
      registerLanguage(language, langModule.default);
      console.debug(`Language ${language} registered for syntax highlighting`);
      resolve();
    } catch (error) {
      console.debug(`Language ${language} not supported for syntax highlighting`);
      reject(error);
    }
  });
};


/**
 * Showdown JS extension for syntax highlighting using Highlight.js. Will attempt to register detected languages.
 */
export const showdownHighlight = (): showdown.FilterExtension => {
  const htmlunencode = (text: string) => {
    return (text
      .replace(/&amp;/g, '&')
      .replace(/&lt;/g, '<')
      .replace(/&gt;/g, '>'));
  };

  const left = '<pre><code\\b[^>]*>';
  const right = '</code></pre>';
  const flags = 'g';
  const replacement = (wholeMatch: string, match: string, leftSide: string, rightSide: string) => {
    const language: string = leftSide.slice(leftSide.indexOf('language-') + ('language-').length,
                                            leftSide.indexOf('"', leftSide.indexOf('language-')));
    addHighlightedLanguage(language).catch(error => null);

    match = htmlunencode(match);
    return leftSide + highlightAuto(match).value + rightSide;
  };

  return {
    type: 'output',
    filter: (text, converter, options) => {
      return (<any>showdown).helper.replaceRecursiveRegExp(text, replacement, left, right, flags);
    }
  };
};


// Import default syntax-highlighting supported languages
highlightedLanguages.forEach((langName) => addHighlightedLanguage(langName));


/**
 * Markdown editor and view module.
 */
@NgModule({
  imports: [],
  declarations: [],
  providers: [
    {provide: 'markdownConverter', useValue: new Converter({extensions: [<any>showdownHighlight]})},
  ],
})
export class MarkdownModule {

}
