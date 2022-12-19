import {VulnerabilitySeverity} from 'src/resources/TagResource';

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
  if (date == -1) {
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
    (sizeInBytes / Math.pow(1024, i)).toFixed(2) * 1 +
    ' ' +
    ['B', 'kB', 'MB', 'GB', 'TB'][i]
  );
}

export function isValidEmail(email: string): boolean {
  const regex = /\S+@\S+\.\S+/;
  return regex.test(email);
}
