import {Tag} from 'src/resources/TagResource';
import {toEpochOrZero} from 'src/libs/utils';

export const extractLastModified = (item: Tag) => item.start_ts || 0;
export const extractExpires = (item: Tag) => toEpochOrZero(item.expiration);
export const extractLastPulled = (item: Tag) => toEpochOrZero(item.last_pulled);
