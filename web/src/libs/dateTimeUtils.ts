export function parseDateTimeValue(value: string): Date | null {
  if (!value) return null;
  const d = new Date(value);
  return isNaN(d.getTime()) ? null : d;
}

export function dateFormat(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

export function dateParse(str: string): Date {
  if (!str) return new Date(NaN);
  const match = str.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!match) return new Date(NaN);
  const year = parseInt(match[1], 10);
  const month = parseInt(match[2], 10);
  const day = parseInt(match[3], 10);
  const createdDate = new Date(year, month - 1, day);
  if (
    createdDate.getFullYear() !== year ||
    createdDate.getMonth() + 1 !== month ||
    createdDate.getDate() !== day
  ) {
    return new Date(NaN);
  }
  return createdDate;
}

export function formatTime(date: Date | null): string {
  if (!date) return '';
  const h = String(date.getHours()).padStart(2, '0');
  const m = String(date.getMinutes()).padStart(2, '0');
  return `${h}:${m}`;
}

export function is24HourFormat(): boolean {
  const resolved = new Intl.DateTimeFormat(undefined, {
    hour: 'numeric',
  }).resolvedOptions();
  return resolved.hour12 !== true;
}

export function formatTimeForPicker(date: Date | null): string {
  if (!date) return '';
  if (is24HourFormat()) {
    return formatTime(date);
  }
  const hours = date.getHours();
  const minutes = String(date.getMinutes()).padStart(2, '0');
  const period = hours >= 12 ? 'PM' : 'AM';
  const h12 = hours % 12 || 12;
  return `${h12}:${minutes} ${period}`;
}

export function getTimezoneLabel(date: Date): string {
  return (
    new Intl.DateTimeFormat(undefined, {timeZoneName: 'longOffset'})
      .formatToParts(date)
      .find((part) => part.type === 'timeZoneName')?.value ?? 'local time'
  );
}

export function toFormString(date: Date): string {
  const y = date.getFullYear();
  const mo = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  const h = String(date.getHours()).padStart(2, '0');
  const mi = String(date.getMinutes()).padStart(2, '0');
  return `${y}-${mo}-${d}T${h}:${mi}`;
}
