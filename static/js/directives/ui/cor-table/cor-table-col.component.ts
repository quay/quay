import { Input, Component, OnInit, Inject, Host } from 'ng-metadata/core';
import { CorTableComponent } from './cor-table.component';


/**
 * Defines a column (optionally sortable) in the table.
 */
@Component({
  selector: 'cor-table-col',
  template: '',
})
export class CorTableColumn implements OnInit {

  @Input('@') public title: string;
  @Input('@') public templateurl: string;
  @Input('@') public datafield: string;
  @Input('@') public sortfield: string;
  @Input('@') public selected: string;
  @Input('=') public bindModel: any;
  @Input('@') public style: string;
  @Input('@') public class: string;
  @Input('@') public kindof: string;
  @Input('<') public itemLimit: number = 5;

  constructor(@Host() @Inject(CorTableComponent) private parent: CorTableComponent,
              @Inject('TableService') private tableService: any) {

  }

  public ngOnInit(): void {
    this.parent.addColumn(this);
  }

  public isNumeric(): boolean {
    return this.kindof == 'datetime';
  }

  public processColumnForOrdered(value: any): any {
    if (this.kindof == 'datetime' && value) {
      return this.tableService.getReversedTimestamp(value);
    }

    return value;
  }
}
