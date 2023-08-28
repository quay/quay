import {Tag} from 'src/resources/TagResource';

export enum TagAction {
  Create = 'create',
  Recreate = 'recreate',
  Delete = 'delete',
  Revert = 'revert',
  Move = 'move',
}

export interface TagEntry {
  tag: Tag;
  time: number; // unix timestamp, milliseconds
  action: TagAction;
  digest: string;
  oldDigest: string;
}
