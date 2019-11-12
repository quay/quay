import { Directive, Inject, Input, AfterContentInit, OnDestroy } from 'ng-metadata/core';
import * as Clipboard from 'clipboard';


@Directive({
  selector: '[clipboardCopy]'
})
export class ClipboardCopyDirective implements AfterContentInit, OnDestroy {

  @Input('@clipboardCopy') public copyTargetSelector: string;

  private clipboard: Clipboard;

  constructor(@Inject('$element') private $element: ng.IAugmentedJQuery,
              @Inject('$timeout') private $timeout: ng.ITimeoutService,
              @Inject('$document') private $document: ng.IDocumentService,
              @Inject('clipboardFactory') private clipboardFactory: (elem, options) => Clipboard) {

  }

  public ngAfterContentInit(): void {
    // FIXME: Need to wait for DOM to render to find target element
    this.$timeout(() => {
      this.clipboard = this.clipboardFactory(this.$element[0], {target: (trigger) => {
          return this.$document[0].querySelector(this.copyTargetSelector);
        }});

      this.clipboard.on("error", (e) => {
        console.error(e);
      });

      this.clipboard.on('success', (e) => {
        const container = e.trigger.parentNode.parentNode.parentNode;
        const messageElem = container.querySelector('.clipboard-copied-message');
        if (!messageElem) {
          return;
        }

        // Resets the animation.
        var elem = messageElem;
        elem.style.display = 'none';
        elem.classList.remove('animated');

        // Show the notification.
        setTimeout(() => {
          elem.style.display = 'inline-block';
          elem.classList.add('animated');
        }, 10);

        // Reset the notification.
        setTimeout(() => {
          elem.style.display = 'none';
        }, 5000);
      });
    }, 100);
  }

  public ngOnDestroy(): void {
    if (this.clipboard) {
      this.clipboard.destroy();
    }
  }
}
