import {setAnonymousMode, isRedirecting} from './axios';

describe('axios exports', () => {
  describe('setAnonymousMode', () => {
    it('does not throw when enabling anonymous mode', () => {
      expect(() => setAnonymousMode(true)).not.toThrow();
    });

    it('does not throw when disabling anonymous mode', () => {
      expect(() => setAnonymousMode(false)).not.toThrow();
    });
  });

  describe('isRedirecting', () => {
    it('returns false by default', () => {
      expect(isRedirecting()).toBe(false);
    });
  });
});
