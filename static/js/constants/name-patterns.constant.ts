/**
 * Regex patterns to for validating account names.
 */
export const NAME_PATTERNS: any = {
  TEAM_PATTERN: '^[a-z][a-z0-9]+$',
  ROBOT_PATTERN: '^[a-z][a-z0-9_]{1,254}$',
  USERNAME_PATTERN: '^(?=.{2,255}$)([a-z0-9]+(?:[._-][a-z0-9]+)*)$',
};
