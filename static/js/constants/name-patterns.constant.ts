/**
 * Regex patterns to for validating account names.
 */
export const NAME_PATTERNS: any = {
  TEAM_PATTERN: '^([a-z0-9]+(?:[._-][a-z0-9]+)*)$',
  ROBOT_PATTERN: '^(?=.{2,255}$)([a-z0-9]+(?:[._-][a-z0-9]+)*)$',
  USERNAME_PATTERN: '^(?=.{2,255}$)([a-z0-9]+(?:[._-][a-z0-9]+)*)$',
};
