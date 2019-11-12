/**
 * Type representing current browser platform.
 * TODO: Add more browser platforms.
 */
export type BrowserPlatform = "firefox"
                            | "chrome";

/**
 * Constant representing current browser platform. Used for determining available features.
 * TODO Only rudimentary implementation, should prefer specific feature detection strategies instead.
 */
export const browserPlatform: BrowserPlatform = (() => {
    if (navigator.userAgent.toLowerCase().indexOf('firefox') != -1) {
      return 'firefox';
    }
    else {
      return 'chrome';
    }
  })();
