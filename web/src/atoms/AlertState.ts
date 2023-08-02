import { ReactNode } from "react";
import { atom } from "recoil";

export enum AlertVariant {
    Success = 'success',
    Failure = 'danger',
}

export interface AlertDetails {
    variant: AlertVariant;
    title: string;
    key?: string;
    message?: string | ReactNode;
}

export const alertState = atom<AlertDetails[]>({
    key: 'alertState',
    default: [],
});
