import { atom } from "recoil";

export enum AlertVariant {
    Success = 'success',
    Failure = 'danger',
}

export interface AlertDetails {
    variant: AlertVariant;
    title: string;
    key?: string;
}

export const alertState = atom<AlertDetails[]>({
    key: 'alertState',
    default: [],
});
