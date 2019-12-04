import { Component, Input, Output, EventEmitter } from 'ng-metadata/core';
import * as template from './repo-state.component.html';
import * as styleUrl from './repo-state.component.css';


type RepoStateOption = {
  value: string;
  title: string;
  description: string;
};

@Component({
  selector: 'repo-state',
  templateUrl: template,
  styleUrls: [styleUrl],
})
export class RepoStateComponent {
  @Input('<') public options: RepoStateOption[];
  @Input('<') public selectedState: RepoStateOption;
  @Output() public onChange = new EventEmitter<RepoStateOption>();
}
