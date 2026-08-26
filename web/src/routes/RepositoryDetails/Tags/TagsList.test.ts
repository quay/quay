import {Tag} from 'src/resources/TagResource';
import {
  extractLastModified,
  extractExpires,
  extractLastPulled,
} from './tagColumnExtractors';

const makeTag = (overrides: Partial<Tag> = {}): Tag =>
  ({
    name: 'latest',
    manifest_digest: 'sha256:abc',
    size: 1024,
    start_ts: 0,
    expiration: undefined,
    last_pulled: undefined,
    ...overrides,
  }) as Tag;

describe('Tag date column extractors (PROJQUAY-11351)', () => {
  describe('extractLastModified', () => {
    it('returns start_ts when present', () => {
      expect(extractLastModified(makeTag({start_ts: 1681393980}))).toBe(
        1681393980,
      );
    });

    it('returns 0 when start_ts is falsy', () => {
      expect(extractLastModified(makeTag({start_ts: 0}))).toBe(0);
      expect(extractLastModified(makeTag({start_ts: undefined}))).toBe(0);
    });
  });

  describe('extractExpires', () => {
    it('returns epoch millis for valid date string', () => {
      const result = extractExpires(
        makeTag({expiration: 'Mon, 13 Apr 2026 12:33:00 -0000'}),
      );
      expect(result).toBe(Date.parse('Mon, 13 Apr 2026 12:33:00 -0000'));
      expect(result).toBeGreaterThan(0);
    });

    it('returns 0 for undefined expiration', () => {
      expect(extractExpires(makeTag({expiration: undefined}))).toBe(0);
    });

    it('returns 0 for empty string expiration', () => {
      expect(extractExpires(makeTag({expiration: ''}))).toBe(0);
    });
  });

  describe('extractLastPulled', () => {
    it('returns epoch millis for valid date string', () => {
      const result = extractLastPulled(
        makeTag({last_pulled: 'Mon, 13 Apr 2026 09:21:00 -0000'}),
      );
      expect(result).toBe(Date.parse('Mon, 13 Apr 2026 09:21:00 -0000'));
      expect(result).toBeGreaterThan(0);
    });

    it('returns 0 for undefined last_pulled', () => {
      expect(extractLastPulled(makeTag({last_pulled: undefined}))).toBe(0);
    });

    it('returns 0 for empty string last_pulled', () => {
      expect(extractLastPulled(makeTag({last_pulled: ''}))).toBe(0);
    });
  });
});
