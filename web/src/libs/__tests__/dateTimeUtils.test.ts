import {
  parseDateTimeValue,
  dateFormat,
  dateParse,
  formatTime,
  formatTimeForPicker,
  is24HourFormat,
  toFormString,
} from 'src/libs/dateTimeUtils';

describe('parseDateTimeValue', () => {
  it('returns null for empty string', () => {
    expect(parseDateTimeValue('')).toBeNull();
  });

  it('returns null for invalid date string', () => {
    expect(parseDateTimeValue('not-a-date')).toBeNull();
  });

  it('parses a valid ISO datetime string', () => {
    const result = parseDateTimeValue('2026-06-15T14:30:00');
    expect(result).toBeInstanceOf(Date);
    expect(result.getFullYear()).toBe(2026);
    expect(result.getMonth()).toBe(5);
    expect(result.getDate()).toBe(15);
  });
});

describe('dateFormat', () => {
  it('formats a date as YYYY-MM-DD', () => {
    expect(dateFormat(new Date(2026, 0, 5))).toBe('2026-01-05');
  });

  it('zero-pads single-digit month and day', () => {
    expect(dateFormat(new Date(2026, 2, 9))).toBe('2026-03-09');
  });

  it('handles double-digit month and day', () => {
    expect(dateFormat(new Date(2026, 11, 25))).toBe('2026-12-25');
  });
});

describe('dateParse', () => {
  it('returns invalid Date for empty string', () => {
    expect(dateParse('').getTime()).toBeNaN();
  });

  it('returns invalid Date for malformed input', () => {
    expect(dateParse('2026/01/15').getTime()).toBeNaN();
    expect(dateParse('01-15-2026').getTime()).toBeNaN();
    expect(dateParse('not-a-date').getTime()).toBeNaN();
  });

  it('parses a valid YYYY-MM-DD string', () => {
    const result = dateParse('2026-03-15');
    expect(result.getFullYear()).toBe(2026);
    expect(result.getMonth()).toBe(2);
    expect(result.getDate()).toBe(15);
  });

  it('rejects Feb 31 (impossible date that would roll over)', () => {
    const result = dateParse('2026-02-31');
    expect(result.getTime()).toBeNaN();
  });

  it('rejects Feb 30', () => {
    const result = dateParse('2026-02-30');
    expect(result.getTime()).toBeNaN();
  });

  it('rejects Feb 29 in a non-leap year', () => {
    const result = dateParse('2025-02-29');
    expect(result.getTime()).toBeNaN();
  });

  it('accepts Feb 29 in a leap year', () => {
    const result = dateParse('2024-02-29');
    expect(result.getFullYear()).toBe(2024);
    expect(result.getMonth()).toBe(1);
    expect(result.getDate()).toBe(29);
  });

  it('rejects Apr 31 (30-day month)', () => {
    expect(dateParse('2026-04-31').getTime()).toBeNaN();
  });

  it('rejects month 13', () => {
    expect(dateParse('2026-13-01').getTime()).toBeNaN();
  });

  it('rejects month 00', () => {
    expect(dateParse('2026-00-15').getTime()).toBeNaN();
  });

  it('rejects day 00', () => {
    expect(dateParse('2026-01-00').getTime()).toBeNaN();
  });

  it('roundtrips with dateFormat', () => {
    const input = '2026-07-04';
    expect(dateFormat(dateParse(input))).toBe(input);
  });
});

describe('formatTime', () => {
  it('returns empty string for null', () => {
    expect(formatTime(null)).toBe('');
  });

  it('formats time as HH:MM with zero-padding', () => {
    expect(formatTime(new Date(2026, 0, 1, 9, 5))).toBe('09:05');
  });

  it('formats midnight as 00:00', () => {
    expect(formatTime(new Date(2026, 0, 1, 0, 0))).toBe('00:00');
  });

  it('formats 23:59', () => {
    expect(formatTime(new Date(2026, 0, 1, 23, 59))).toBe('23:59');
  });
});

describe('is24HourFormat', () => {
  it('returns a boolean', () => {
    expect(typeof is24HourFormat()).toBe('boolean');
  });
});

describe('formatTimeForPicker', () => {
  it('returns empty string for null', () => {
    expect(formatTimeForPicker(null)).toBe('');
  });

  it('returns a non-empty string for a valid date', () => {
    const result = formatTimeForPicker(new Date(2026, 0, 1, 14, 30));
    expect(result).not.toBe('');
    // Should contain "14:30" (24h) or "2:30 PM" (12h)
    expect(result).toMatch(/14:30|2:30 PM/);
  });

  it('formats midnight correctly', () => {
    const result = formatTimeForPicker(new Date(2026, 0, 1, 0, 0));
    expect(result).toMatch(/00:00|12:00 AM/);
  });

  it('formats noon correctly', () => {
    const result = formatTimeForPicker(new Date(2026, 0, 1, 12, 0));
    expect(result).toMatch(/12:00|12:00 PM/);
  });
});

describe('toFormString', () => {
  it('formats date as YYYY-MM-DDTHH:MM', () => {
    const result = toFormString(new Date(2026, 5, 15, 14, 30));
    expect(result).toBe('2026-06-15T14:30');
  });

  it('zero-pads all components', () => {
    const result = toFormString(new Date(2026, 0, 5, 3, 7));
    expect(result).toBe('2026-01-05T03:07');
  });

  it('roundtrips with parseDateTimeValue', () => {
    const original = new Date(2026, 8, 20, 16, 45);
    const str = toFormString(original);
    const parsed = parseDateTimeValue(str);
    expect(parsed.getFullYear()).toBe(original.getFullYear());
    expect(parsed.getMonth()).toBe(original.getMonth());
    expect(parsed.getDate()).toBe(original.getDate());
    expect(parsed.getHours()).toBe(original.getHours());
    expect(parsed.getMinutes()).toBe(original.getMinutes());
  });
});
