import {
  parseDateTimeValue,
  dateFormat,
  dateParse,
  formatTime,
  is24HourFormat,
  formatTimeForPicker,
  getTimezoneLabel,
  toFormString,
} from './dateTimeUtils';

describe('parseDateTimeValue', () => {
  it('parses valid ISO string', () => {
    const result = parseDateTimeValue('2024-03-15T14:30:00Z');
    expect(result).toBeInstanceOf(Date);
    expect(result!.getTime()).not.toBeNaN();
  });

  it('returns null for invalid string', () => {
    expect(parseDateTimeValue('not-a-date')).toBeNull();
  });

  it('returns null for empty string', () => {
    expect(parseDateTimeValue('')).toBeNull();
  });
});

describe('dateFormat', () => {
  it('formats date as YYYY-MM-DD', () => {
    const date = new Date(2024, 2, 15); // March 15, 2024
    expect(dateFormat(date)).toBe('2024-03-15');
  });

  it('pads single-digit month and day', () => {
    const date = new Date(2024, 0, 5); // Jan 5, 2024
    expect(dateFormat(date)).toBe('2024-01-05');
  });
});

describe('dateParse', () => {
  it('parses valid YYYY-MM-DD string', () => {
    const result = dateParse('2024-03-15');
    expect(result.getFullYear()).toBe(2024);
    expect(result.getMonth()).toBe(2); // March = 2
    expect(result.getDate()).toBe(15);
  });

  it('returns NaN date for empty string', () => {
    expect(dateParse('').getTime()).toBeNaN();
  });

  it('returns NaN date for wrong format', () => {
    expect(dateParse('03/15/2024').getTime()).toBeNaN();
    expect(dateParse('2024-3-15').getTime()).toBeNaN();
  });

  it('returns NaN date for invalid calendar dates', () => {
    // Feb 30 doesn't exist — JS Date rolls over to March
    expect(dateParse('2024-02-30').getTime()).toBeNaN();
    // Month 13 doesn't exist
    expect(dateParse('2024-13-01').getTime()).toBeNaN();
  });
});

describe('formatTime', () => {
  it('formats date to HH:MM', () => {
    const date = new Date(2024, 0, 1, 14, 5);
    expect(formatTime(date)).toBe('14:05');
  });

  it('returns empty string for null', () => {
    expect(formatTime(null)).toBe('');
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

  it('returns a non-empty string for valid date', () => {
    const date = new Date(2024, 0, 1, 14, 30);
    const result = formatTimeForPicker(date);
    expect(result.length).toBeGreaterThan(0);
  });
});

describe('getTimezoneLabel', () => {
  it('returns a timezone string', () => {
    const date = new Date();
    const label = getTimezoneLabel(date);
    expect(typeof label).toBe('string');
    expect(label.length).toBeGreaterThan(0);
  });
});

describe('toFormString', () => {
  it('formats date to YYYY-MM-DDTHH:MM', () => {
    const date = new Date(2024, 2, 15, 9, 5); // March 15, 2024 09:05
    expect(toFormString(date)).toBe('2024-03-15T09:05');
  });

  it('pads all components', () => {
    const date = new Date(2024, 0, 1, 1, 1); // Jan 1, 2024 01:01
    expect(toFormString(date)).toBe('2024-01-01T01:01');
  });
});
