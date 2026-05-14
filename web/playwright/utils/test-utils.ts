import {randomBytes} from 'node:crypto';

export function uniqueName(prefix: string): string {
  const rand = randomBytes(4).toString('hex').substring(0, 8);
  return `${prefix}-${Date.now()}-${rand}`;
}
