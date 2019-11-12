import { ViewArray } from './view-array';
import { Injectable, Inject } from 'ng-metadata/core';


@Injectable(ViewArray.name)
export class ViewArrayImpl implements ViewArray {

  public entries: any[];
  public isVisible: boolean;
  public visibleEntries: any[];
  public hasEntries: boolean;
  public hasHiddenEntries: boolean;
  private timerRef: any;
  private currentIndex: number;
  private additionalCount: number = 20;

  constructor(@Inject('$interval') private $interval: ng.IIntervalService) {
    this.isVisible = false;
    this.visibleEntries = null;
    this.hasEntries = false;
    this.entries = [];
    this.hasHiddenEntries = false;
    this.timerRef = null;
    this.currentIndex = 0;
  }

  public length(): number {
    return this.entries.length;
  }

  public get(index: number): any {
    return this.entries[index];
  }

  public push(elem: any): void {
    this.entries.push(elem);
    this.hasEntries = true;

    if (this.isVisible) {
      this.startTimer();
    }
  }

  public toggle(): void {
    this.setVisible(!this.isVisible);
  }

  public setVisible(newState: boolean): void {
    this.isVisible = newState;

    this.visibleEntries = [];
    this.currentIndex = 0;

    if (newState) {
      this.showAdditionalEntries();
      this.startTimer();
    }
    else {
      this.stopTimer();
    }
  }

  public create(): ViewArrayImpl {
    return new ViewArrayImpl(this.$interval);
  }

  private showAdditionalEntries(): void {
    var i: number = 0;
    for (i = this.currentIndex; i < (this.currentIndex + this.additionalCount) && i < this.entries.length; ++i) {
      this.visibleEntries.push(this.entries[i]);
    }

    this.currentIndex = i;
    this.hasHiddenEntries = this.currentIndex < this.entries.length;
    if (this.currentIndex >= this.entries.length) {
      this.stopTimer();
    }
  }

  private startTimer(): void {
    if (this.timerRef) {
      return;
    }

    this.timerRef = this.$interval(() => {
      this.showAdditionalEntries();
    }, 10);
  }

  private stopTimer(): void {
    if (this.timerRef) {
      this.$interval.cancel(this.timerRef);
      this.timerRef = null;
    }
  }
}
