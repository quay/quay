import {VulnerabilitySeverity} from 'src/resources/TagResource';
import moment from 'moment';

export function getSeverityColor(severity: VulnerabilitySeverity) {
  switch (severity) {
    case VulnerabilitySeverity.Critical:
      return '#7D1007';
    case VulnerabilitySeverity.High:
      return '#C9190B';
    case VulnerabilitySeverity.Medium:
      return '#EC7A08';
    case VulnerabilitySeverity.Low:
      return '#F0AB00';
    case VulnerabilitySeverity.None:
      return '#3E8635';
    default:
      return '#8A8D90';
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

export function parseRepoNameFromUrl(url: string): string {
  //url is in the format of <prefix>/repository/<org>/<repo>
  //or for nested repo: <prefix>/repository/<org>/<nested>/<repo>
  //or <prefix>/repository/<org>/<repo>/tag/<tag>
  const urlParts = url.split('/');
  const repoKeywordIndex = urlParts.indexOf('repository');
  let endIndex = urlParts.indexOf('tag');
  if (repoKeywordIndex === -1) {
    return '';
  }

  if (endIndex === -1) {
    endIndex = urlParts.length;
  }
  // Taking nested repos into consideration
  return urlParts.slice(repoKeywordIndex + 2, endIndex).join('/');
}

export function parseOrgNameFromUrl(url: string): string {
  //url is in the format of <prefix>/repository/<org>/<repo>
  //or <prefix>/repository/<org>/<repo>/tag/<tag>
  const urlParts = url.split('/');
  const repoKeywordIndex = urlParts.indexOf('repository');
  if (repoKeywordIndex === -1) {
    return '';
  }
  return urlParts[repoKeywordIndex + 1];
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

export function humanizeTimeForExpiry(time_seconds: number): string {
  return moment.duration(time_seconds || 0, 's').humanize();
}

export function getSeconds(duration_str: string): number {
  if (!duration_str) {
    return 0;
  }

  let [number, suffix] = duration_str.split('');
  return moment.duration(parseInt(number), suffix).asSeconds();
}

export function isNullOrUndefined(obj: any): boolean {
  return obj === null || obj === undefined;
}
