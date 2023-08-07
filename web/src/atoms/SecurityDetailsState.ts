import { DefaultValue, atom, atomFamily, selectorFamily } from 'recoil';
import { SecurityDetailsResponse } from 'src/resources/TagResource';

export const SecurityDetailsState = atom<SecurityDetailsResponse>({
  key: 'securityDetailsState',
  default: null,
});

export const SecurityDetailsErrorState = atom<string>({
  key: 'securityDetailsErrorState',
  default: null,
});

// keeps track of the call state of the security details API per digest
export const SecurityDetailsCallState = atomFamily<boolean, string>({
  key: 'securityDetailsCallState',
  default: undefined,
})

// keeps track of all calls to the security details API
export const SecurityDetailsCallStates = atom<string[]>({
  key: 'securityDetailsCallStates',
  default: [],
})

// this is a selector returns/or sets the call state of a single security details call as an atom 
// and keeps track of all calls to the security details API in a separate atom
export const securityDetailsCallStateSelector = selectorFamily<boolean, string>({
  key: "securityDetailsCallStateSelector",
  get: (digest: string) => ({ get }) => {
    return get(SecurityDetailsCallState(digest));
  },
  set: (digest: string) => ({ set, reset }, newSecurityDetailsCallState) => {
    if (newSecurityDetailsCallState instanceof DefaultValue) {
      reset(SecurityDetailsCallState(digest));
      set(SecurityDetailsCallStates, (prevValue: string[]) => prevValue.filter((id: string) => id !== digest));
    } else {
      set(SecurityDetailsCallState(digest), newSecurityDetailsCallState);
      set(SecurityDetailsCallStates, (prev) => [...prev, digest]);
    }
  },
});

// this selector returns the call state of all security details calls as an atom and inverts all atoms
export const securityDetailsCallStatesInverter = selectorFamily({
  key: "securityDetailsCallStatesSelector",
  get: (digests: string[]) => ({ get }) => {
    return digests.map((digest) => get(securityDetailsCallStateSelector(digest)));
  },
  set: (digests: string[]) => ({ get, set, }, _) => {
    // invert all atoms in the atomFamily
    digests.forEach((digest) => {
      set(securityDetailsCallStateSelector(digest), !get(securityDetailsCallStateSelector(digest)))
    });
  }
});
