import {VulnerabilitySeverity} from 'src/resources/TagResource';
import moment from 'moment';
import {ITeamMember} from 'src/hooks/UseMembers';

export function getSeverityColor(severity: VulnerabilitySeverity) {
  switch (severity) {
    case VulnerabilitySeverity.Critical:
      return 'var(--pf-v5-global--palette--red-200)';
    case VulnerabilitySeverity.High:
      return 'var(--pf-v5-global--palette--red-100)';
    case VulnerabilitySeverity.Medium:
      return 'var(--pf-v5-global--palette--orange-300)';
    case VulnerabilitySeverity.Low:
      return 'var(--pf-v5-global--palette--gold-300)';
    case VulnerabilitySeverity.None:
      return 'var(--pf-v5-global--palette--green-400)';
    default:
      return 'var(--pf-v5-global--palette--black-300)';
  }
}

export function formatDate(date: string | number) {
  if (!date || date == -1) {
    return 'N/A';
  }

  const adjustedDate = typeof date === 'number' ? date * 1000 : date;
  return new Date(adjustedDate).toLocaleString('en-US', {
    timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    timeStyle: 'short',
    dateStyle: 'medium',
  });
}

export function formatSize(sizeInBytes: number) {
  if (!sizeInBytes) {
    // null or undefined
    return 'N/A';
  }

  const i = Math.floor(Math.log(sizeInBytes) / Math.log(1024));
  return (
    (sizeInBytes / Math.pow(1024, i)).toFixed(2) +
    ' ' +
    ['B', 'kB', 'MB', 'GB', 'TB'][i]
  );
}

export function isValidEmail(email: string): boolean {
  const regex = /\S+@\S+\.\S+/;
  return regex.test(email);
}

export const validateTeamName = (name: string) => {
  return /^[a-z][a-z0-9]+$/.test(name);
};

export function parseRepoNameFromUrl(url: string): string {
  //url is in the format of <prefix>/repository/<org>/<repo>
  //or for nested repo: <prefix>/repository/<org>/<nested>/<repo>
  //or <prefix>/repository/<org>/<repo>/tag/<tag>
  const urlParts = url.split('/');
  const repoKeywordIndex = urlParts.indexOf('repository');
  if (repoKeywordIndex === -1) {
    return '';
  }

  let endIndex = urlParts.lastIndexOf('tag');
  if (endIndex === -1) {
    endIndex = urlParts.lastIndexOf('build');
  }

  if (endIndex === -1) {
    endIndex = urlParts.length;
  }
  // Taking nested repos into consideration
  return urlParts.slice(repoKeywordIndex + 2, endIndex).join('/');
}

export function parseOrgNameFromUrl(url: string): string {
  //url is in the format of <prefix>/repository/<org>/<repo> or <prefix>/organization/<org>/<repo>
  //or <prefix>/repository/<org>/<repo>/tag/<tag>
  const urlParts = url.split('/');
  const repoKeywordIndex = urlParts.indexOf('repository');
  const orgKeywordIndex = urlParts.indexOf('organization');
  if (repoKeywordIndex != -1) {
    return urlParts[repoKeywordIndex + 1];
  }

  if (orgKeywordIndex === -1) {
    return '';
  }

  return urlParts[orgKeywordIndex + 1];
}

export function parseTagNameFromUrl(url: string): string {
  //url is in the format of <prefix>/repository/<org>/<repo>
  //or <prefix>/repository/<org>/<repo>/tag/<tag>

  const urlParts = url.split('/');
  const repoKeywordIndex = urlParts.indexOf('repository');
  const tagKeywordIndex = urlParts.indexOf('tag');

  if (repoKeywordIndex === -1) {
    return '';
  }

  if (tagKeywordIndex === -1) {
    return '';
  }

  return urlParts[tagKeywordIndex + 1];
}

export function parseTeamNameFromUrl(url: string): string {
  //url is in the format of <prefix>/organization/<org>/teams/<team>
  const urlParts = url.split('/');
  const teamKeywordIndex = urlParts.indexOf('teams');
  if (teamKeywordIndex === -1) {
    return '';
  }
  return urlParts[teamKeywordIndex + 1];
}

export function humanizeTimeForExpiry(time_seconds: number): string {
  return moment.duration(time_seconds || 0, 's').humanize();
}

export function getSeconds(duration_str: string): number {
  if (!duration_str) {
    return 0;
  }

  const [number, suffix] = duration_str.split('');
  return moment.duration(parseInt(number), suffix).asSeconds();
}

export function isNullOrUndefined(obj: any): boolean {
  return obj === null || obj === undefined;
}

export const getAccountTypeForMember = (member: ITeamMember): string => {
  if (member.is_robot) {
    return 'Robot account';
  } else if (!member.is_robot && !member.invited) {
    return 'Team member';
  } else if (member.invited) {
    return '(Invited)';
  }
};

export const titleCase = (str: string): string => {
  return str.charAt(0).toUpperCase() + str.slice(1);
};

export const escapeHtmlString = function (text) {
  const textStr = (text || '').toString();
  const adjusted = textStr
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');

  return adjusted;
};
