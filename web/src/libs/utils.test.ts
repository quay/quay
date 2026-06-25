import React from 'react';
import moment from 'moment';
import {ITeamMember} from 'src/hooks/UseMembers';
import {VulnerabilitySeverity} from 'src/resources/TagResource';
import {
  formatSize,
  isValidEmail,
  validateTeamName,
  parseRepoNameFromUrl,
  parseOrgNameFromUrl,
  parseTagNameFromUrl,
  parseTeamNameFromUrl,
  titleCase,
  escapeHtmlString,
  convertToSeconds,
  convertFromSeconds,
  isNullOrUndefined,
  formatDateForInput,
  getAccountTypeForMember,
  getSeverityColor,
  formatDate,
  parseTimeDuration,
  humanizeTimeForExpiry,
  getSeconds,
  formatRelativeTime,
  extractTextFromReactNode,
  toEpochOrZero,
} from './utils';

describe('formatSize', () => {
  it('returns N/A for null', () => {
    expect(formatSize(null as unknown as number)).toBe('N/A');
  });

  it('returns N/A for undefined', () => {
    expect(formatSize(undefined as unknown as number)).toBe('N/A');
  });

  it('returns 0.00 KiB for 0', () => {
    expect(formatSize(0)).toBe('0.00 KiB');
  });

  it('formats bytes', () => {
    expect(formatSize(500)).toBe('500.00 B');
  });

  it('formats kibibytes', () => {
    expect(formatSize(1024)).toBe('1.00 KiB');
    expect(formatSize(1536)).toBe('1.50 KiB');
  });

  it('formats mebibytes', () => {
    expect(formatSize(1048576)).toBe('1.00 MiB');
  });

  it('formats gibibytes', () => {
    expect(formatSize(1073741824)).toBe('1.00 GiB');
  });
});

describe('isValidEmail', () => {
  it('accepts valid emails', () => {
    expect(isValidEmail('user@example.com')).toBe(true);
    expect(isValidEmail('test@test.co.uk')).toBe(true);
  });

  it('rejects invalid emails', () => {
    expect(isValidEmail('')).toBe(false);
    expect(isValidEmail('notanemail')).toBe(false);
    expect(isValidEmail('@missing.user')).toBe(false);
    expect(isValidEmail('no@tld')).toBe(false);
  });
});

describe('validateTeamName', () => {
  it('accepts valid team names', () => {
    expect(validateTeamName('myteam')).toBe(true);
    expect(validateTeamName('my-team')).toBe(true);
    expect(validateTeamName('my.team')).toBe(true);
    expect(validateTeamName('my_team')).toBe(true);
    expect(validateTeamName('team123')).toBe(true);
  });

  it('rejects invalid team names', () => {
    expect(validateTeamName('MyTeam')).toBe(false);
    expect(validateTeamName('my team')).toBe(false);
    expect(validateTeamName('')).toBe(false);
    expect(validateTeamName('-team')).toBe(false);
    expect(validateTeamName('team-')).toBe(false);
  });
});

describe('parseRepoNameFromUrl', () => {
  it('parses simple repo name', () => {
    expect(parseRepoNameFromUrl('/repository/org/repo')).toBe('repo');
  });

  it('parses nested repo name', () => {
    expect(parseRepoNameFromUrl('/repository/org/nested/repo')).toBe(
      'nested/repo',
    );
  });

  it('strips tag suffix', () => {
    expect(parseRepoNameFromUrl('/repository/org/repo/tag/latest')).toBe(
      'repo',
    );
  });

  it('strips build suffix', () => {
    expect(parseRepoNameFromUrl('/repository/org/repo/build/abc123')).toBe(
      'repo',
    );
  });

  it('returns empty string without repository keyword', () => {
    expect(parseRepoNameFromUrl('/org/repo')).toBe('');
  });
});

describe('parseOrgNameFromUrl', () => {
  it('parses org from repository URL', () => {
    expect(parseOrgNameFromUrl('/repository/myorg/myrepo')).toBe('myorg');
  });

  it('parses org from organization URL', () => {
    expect(parseOrgNameFromUrl('/organization/myorg')).toBe('myorg');
  });

  it('returns empty string for unrecognized URL', () => {
    expect(parseOrgNameFromUrl('/some/path')).toBe('');
  });
});

describe('parseTagNameFromUrl', () => {
  it('parses tag name from URL', () => {
    expect(parseTagNameFromUrl('/repository/org/repo/tag/latest')).toBe(
      'latest',
    );
  });

  it('returns empty string when no tag in URL', () => {
    expect(parseTagNameFromUrl('/repository/org/repo')).toBe('');
  });

  it('returns empty string when no repository keyword', () => {
    expect(parseTagNameFromUrl('/some/path/tag/v1')).toBe('');
  });
});

describe('parseTeamNameFromUrl', () => {
  it('parses team name', () => {
    expect(parseTeamNameFromUrl('/organization/myorg/teams/devs')).toBe('devs');
  });

  it('returns empty string without teams keyword', () => {
    expect(parseTeamNameFromUrl('/organization/myorg')).toBe('');
  });
});

describe('titleCase', () => {
  it('capitalizes first letter', () => {
    expect(titleCase('hello')).toBe('Hello');
    expect(titleCase('world')).toBe('World');
  });

  it('leaves rest of string unchanged', () => {
    expect(titleCase('hELLO')).toBe('HELLO');
  });
});

describe('escapeHtmlString', () => {
  it('escapes HTML entities', () => {
    expect(escapeHtmlString('<script>alert("xss")</script>')).toBe(
      '&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;',
    );
  });

  it('escapes ampersand', () => {
    expect(escapeHtmlString('a&b')).toBe('a&amp;b');
  });

  it('escapes single quotes', () => {
    expect(escapeHtmlString("it's")).toBe('it&#039;s');
  });

  it('handles null/undefined', () => {
    expect(escapeHtmlString(null)).toBe('');
    expect(escapeHtmlString(undefined)).toBe('');
  });
});

describe('convertToSeconds / convertFromSeconds', () => {
  it('converts minutes to seconds', () => {
    expect(convertToSeconds(5, 'minutes')).toBe(300);
  });

  it('converts hours to seconds', () => {
    expect(convertToSeconds(2, 'hours')).toBe(7200);
  });

  it('converts days to seconds', () => {
    expect(convertToSeconds(1, 'days')).toBe(86400);
  });

  it('converts weeks to seconds', () => {
    expect(convertToSeconds(1, 'weeks')).toBe(604800);
  });

  it('round-trips correctly', () => {
    const seconds = convertToSeconds(3, 'hours');
    const result = convertFromSeconds(seconds);
    expect(result).toEqual({value: 3, unit: 'hours'});
  });

  it('picks the largest clean unit', () => {
    expect(convertFromSeconds(604800)).toEqual({value: 1, unit: 'weeks'});
    expect(convertFromSeconds(86400)).toEqual({value: 1, unit: 'days'});
    expect(convertFromSeconds(3600)).toEqual({value: 1, unit: 'hours'});
    expect(convertFromSeconds(60)).toEqual({value: 1, unit: 'minutes'});
    expect(convertFromSeconds(1)).toEqual({value: 1, unit: 'seconds'});
  });
});

describe('isNullOrUndefined', () => {
  it('returns true for null and undefined', () => {
    expect(isNullOrUndefined(null)).toBe(true);
    expect(isNullOrUndefined(undefined)).toBe(true);
  });

  it('returns false for other values', () => {
    expect(isNullOrUndefined(0)).toBe(false);
    expect(isNullOrUndefined('')).toBe(false);
    expect(isNullOrUndefined(false)).toBe(false);
  });
});

describe('formatDateForInput', () => {
  it('formats ISO date to datetime-local format', () => {
    const result = formatDateForInput('2024-03-15T14:30:00Z');
    // Result depends on local timezone, but should match pattern
    expect(result).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/);
  });

  it('returns empty string for empty input', () => {
    expect(formatDateForInput('')).toBe('');
  });

  it('returns empty string for invalid date', () => {
    expect(formatDateForInput('not-a-date')).toBe('');
  });
});

describe('getAccountTypeForMember', () => {
  it('returns Robot account for robots', () => {
    const member = {
      name: 'bot',
      kind: 'user',
      is_robot: true,
      invited: false,
    } as unknown as ITeamMember;
    expect(getAccountTypeForMember(member)).toBe('Robot account');
  });

  it('returns Team member for non-robot, non-invited', () => {
    const member: ITeamMember = {
      name: 'user',
      kind: 'user',
      is_robot: false,
      invited: false,
    };
    expect(getAccountTypeForMember(member)).toBe('Team member');
  });

  it('returns (Invited) for invited members', () => {
    const member: ITeamMember = {
      name: 'user',
      kind: 'user',
      is_robot: false,
      invited: true,
    };
    expect(getAccountTypeForMember(member)).toBe('(Invited)');
  });
});

describe('getSeverityColor', () => {
  it('returns correct CSS var for each severity', () => {
    expect(getSeverityColor(VulnerabilitySeverity.Critical)).toContain(
      'critical',
    );
    expect(getSeverityColor(VulnerabilitySeverity.High)).toContain('important');
    expect(getSeverityColor(VulnerabilitySeverity.Medium)).toContain(
      'moderate',
    );
    expect(getSeverityColor(VulnerabilitySeverity.Low)).toContain('minor');
    expect(getSeverityColor(VulnerabilitySeverity.None)).toContain('none');
  });

  it('returns undefined color for unknown severity', () => {
    expect(
      getSeverityColor('InvalidSeverity' as VulnerabilitySeverity),
    ).toContain('undefined');
  });
});

describe('formatDate', () => {
  it('returns N/A for falsy values', () => {
    expect(formatDate('')).toBe('N/A');
    expect(formatDate(0)).toBe('N/A');
  });

  it('returns N/A for -1', () => {
    expect(formatDate(-1)).toBe('N/A');
  });

  it('formats unix timestamp (seconds)', () => {
    // 1704067200 = 2024-01-01T00:00:00Z — function multiplies by 1000
    const result = formatDate(1704067200);
    expect(typeof result).toBe('string');
    expect(result).not.toBe('N/A');
  });

  it('formats ISO string', () => {
    const result = formatDate('2024-06-15T12:00:00Z');
    expect(typeof result).toBe('string');
    expect(result).not.toBe('N/A');
  });
});

describe('parseTimeDuration', () => {
  it('parses valid durations', () => {
    expect(parseTimeDuration('5s').asSeconds()).toBe(5);
    expect(parseTimeDuration('30m').asMinutes()).toBe(30);
    expect(parseTimeDuration('2h').asHours()).toBe(2);
    expect(parseTimeDuration('7d').asDays()).toBe(7);
  });

  it('returns invalid duration for bad input', () => {
    expect(parseTimeDuration('').isValid()).toBe(false);
    expect(parseTimeDuration('abc').isValid()).toBe(false);
    expect(parseTimeDuration('10x').isValid()).toBe(false);
  });
});

describe('humanizeTimeForExpiry', () => {
  it('humanizes short durations (<31 days)', () => {
    const result = humanizeTimeForExpiry(86400); // 1 day
    expect(typeof result).toBe('string');
    expect(result.length).toBeGreaterThan(0);
  });

  it('shows days for mid-range durations where months are ambiguous', () => {
    // 45 days — not close to a month boundary
    const result = humanizeTimeForExpiry(45 * 86400);
    expect(result).toContain('45 days');
  });

  it('humanizes long durations (>365 days)', () => {
    const result = humanizeTimeForExpiry(400 * 86400); // ~1 year 1 month
    expect(result).toContain('1 years');
  });

  it('accepts moment Duration input', () => {
    const duration = moment.duration(7, 'days');
    const result = humanizeTimeForExpiry(duration);
    expect(typeof result).toBe('string');
    expect(result.length).toBeGreaterThan(0);
  });
});

describe('getSeconds', () => {
  it('converts single-digit value with suffix', () => {
    // Note: getSeconds splits on '' (each character), so only
    // single-digit numbers work correctly
    expect(getSeconds('5s')).toBe(5);
    expect(getSeconds('2h')).toBe(7200);
  });

  it('returns 0 for empty string', () => {
    expect(getSeconds('')).toBe(0);
  });
});

describe('formatRelativeTime', () => {
  it('returns Never for falsy values', () => {
    expect(formatRelativeTime('')).toBe('Never');
    expect(formatRelativeTime(0)).toBe('Never');
  });

  it('returns Never for -1', () => {
    expect(formatRelativeTime(-1)).toBe('Never');
  });

  it('returns Never for "Never" string', () => {
    expect(formatRelativeTime('Never')).toBe('Never');
  });

  it('returns a relative time string for valid dates', () => {
    const result = formatRelativeTime(Date.now() / 1000 - 3600); // 1 hour ago
    expect(typeof result).toBe('string');
    expect(result).not.toBe('Never');
  });
});

describe('toEpochOrZero', () => {
  it('returns 0 for undefined', () => {
    expect(toEpochOrZero(undefined)).toBe(0);
  });

  it('returns 0 for empty string', () => {
    expect(toEpochOrZero('')).toBe(0);
  });

  it('parses valid RFC 2822 date string', () => {
    const result = toEpochOrZero('Mon, 13 Apr 2026 12:33:00 -0000');
    expect(result).toBe(Date.parse('Mon, 13 Apr 2026 12:33:00 -0000'));
    expect(result).toBeGreaterThan(0);
  });

  it('parses valid ISO 8601 date string', () => {
    const result = toEpochOrZero('2026-04-13T12:33:00Z');
    expect(result).toBe(Date.parse('2026-04-13T12:33:00Z'));
  });

  it('returns 0 for invalid date string', () => {
    expect(toEpochOrZero('not-a-date')).toBe(0);
  });

  it('returns 0 for malformed date string', () => {
    expect(toEpochOrZero('99/99/9999')).toBe(0);
  });
});

describe('extractTextFromReactNode', () => {
  it('extracts text from strings', () => {
    expect(extractTextFromReactNode('hello')).toBe('hello');
  });

  it('extracts text from numbers', () => {
    expect(extractTextFromReactNode(42)).toBe('42');
  });

  it('returns empty string for null/undefined/boolean', () => {
    expect(extractTextFromReactNode(null)).toBe('');
    expect(extractTextFromReactNode(undefined)).toBe('');
    expect(extractTextFromReactNode(true)).toBe('');
  });

  it('extracts text from arrays', () => {
    expect(extractTextFromReactNode(['hello', ' ', 'world'])).toBe(
      'hello world',
    );
  });

  it('extracts text from nested React elements', () => {
    const node = React.createElement(
      'span',
      null,
      'Push of ',
      React.createElement('code', null, 'tag123'),
      ' to repo',
    );
    expect(extractTextFromReactNode(node)).toBe('Push of tag123 to repo');
  });
});
