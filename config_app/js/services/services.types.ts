export interface AngularPollChannel {
    create: PollConstructor
}

type PollConstructor = (scope: MockAngularScope, requester: ShouldContinueCallback, opt_sleeptime?: number) => PollHandle;
type MockAngularScope = {
    '$on': Function
};
type ShouldContinueCallback = (boolean) => void;

export interface PollHandle {
    start(opt_skipFirstCall?: boolean): void,
    stop(): void,
    setSleepTime(sleepTime: number): void,
}
