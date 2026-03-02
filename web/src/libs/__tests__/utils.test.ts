import {formatDateForInput} from 'src/libs/utils';

describe('formatDateForInput', () => {
  it('returns empty string for empty input', () => {
    expect(formatDateForInput('')).toBe('');
  });

  it('returns empty string for invalid date', () => {
    expect(formatDateForInput('not-a-date')).toBe('');
  });

  it('converts UTC ISO date to local datetime-local format', () => {
    const input = '2026-06-15T14:30:00Z';
    const date = new Date(input);
    const expected =
      [
        date.getFullYear(),
        String(date.getMonth() + 1).padStart(2, '0'),
        String(date.getDate()).padStart(2, '0'),
      ].join('-') +
      'T' +
      [
        String(date.getHours()).padStart(2, '0'),
        String(date.getMinutes()).padStart(2, '0'),
      ].join(':');

    expect(formatDateForInput(input)).toBe(expected);
  });

  it('handles ISO dates with timezone offsets', () => {
    const input = '2026-03-10T08:00:00+05:30';
    const date = new Date(input);
    const expected =
      [
        date.getFullYear(),
        String(date.getMonth() + 1).padStart(2, '0'),
        String(date.getDate()).padStart(2, '0'),
      ].join('-') +
      'T' +
      [
        String(date.getHours()).padStart(2, '0'),
        String(date.getMinutes()).padStart(2, '0'),
      ].join(':');

    expect(formatDateForInput(input)).toBe(expected);
  });

  it('produces output in YYYY-MM-DDTHH:MM format', () => {
    const result = formatDateForInput('2026-01-15T10:00:00Z');
    expect(result).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/);
  });
});
