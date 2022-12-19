import {atom} from 'recoil';
import {SecurityDetailsResponse} from 'src/resources/TagResource';

export const SecurityDetailsState = atom<SecurityDetailsResponse>({
  key: 'securityDetailsState',
  default: null,
});

export const SecurityDetailsErrorState = atom<string>({
  key: 'securityDetailsErrorState',
  default: null,
});
