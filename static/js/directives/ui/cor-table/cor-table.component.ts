import { Input, Component, OnChanges, SimpleChanges, Inject } from 'ng-metadata/core';
import { CorTableColumn } from './cor-table-col.component';
import { ViewArray } from '../../../services/view-array/view-array';
import './cor-table.component.css';


/**
 * A component that displays a table of information, with optional filtering and automatic sorting.
 */
@Component({
  selector: 'cor-table',
  templateUrl: '/static/js/directives/ui/cor-table/cor-table.component.html',
  legacy: {
    transclude: true
  }
})
export class CorTableComponent implements OnChanges {

  @Input('<') public tableData: any[] = [];
  @Input('@') public tableItemTitle: string;
  @Input('<') public filterFields: string[];
  @Input('<') public compact: boolean = false;
  @Input('<') public maxDisplayCount: number = 10;
  @Input('<') public canExpand: boolean = false;
  @Input('<') public expandRows: boolean = false;

  public orderedData: ViewArray;
  public options: CorTableOptions = {
    filter: '',
    reverse: false,
    predicate: '',
    page: 0,
  };

  private rows: CorTableRow[] = [];
  private columns: CorTableColumn[] = [];

  constructor(@Inject('TableService') private tableService: any) {

  }

  public ngOnChanges(changes: SimpleChanges): void {
    if (changes['tableData'] !== undefined) {
      this.refreshOrder();
    }
  }

  public addColumn(col: CorTableColumn): void {
    this.columns.push(col);

    if (col.selected == 'true') {
      this.options['predicate'] = col.datafield;
    }

    this.refreshOrder();
  }

  private setOrder(col: CorTableColumn): void {
    this.tableService.orderBy(col.datafield, this.options);
    this.refreshOrder();
  }

  private setExpanded(isExpanded: boolean): void {
    this.expandRows = isExpanded;
    this.rows.forEach((row) => row.expanded = isExpanded);
  }

  private tablePredicateClass(col: CorTableColumn, options: any) {
    return this.tableService.tablePredicateClass(col.datafield, this.options.predicate, this.options.reverse);
  }

  private refreshOrder(): void {
    this.options.page = 0;

    var columnMap: {[name: string]: CorTableColumn} = {};
    this.columns.forEach(function(col) {
      columnMap[col.datafield] = col;
    });

    const numericCols: string[] = this.columns.filter(col => col.isNumeric())
      .map(col => col.datafield);

    const processed: any[] = this.tableData.map((item) => {
      Object.keys(item).forEach((key) => {
        if (columnMap[key]) {
          item[key] = columnMap[key].processColumnForOrdered(item[key]);
        }
      });

      return item;
    });

    this.orderedData = this.tableService.buildOrderedItems(processed, this.options, this.filterFields, numericCols);
    this.rows = this.orderedData.visibleEntries.map((item) => Object.assign({}, {expanded: false, rowData: item}));
  }
}


export type CorTableOptions = {
  filter: string;
  reverse: boolean;
  predicate: string;
  page: number;
};


export type CorTableRow = {
  expanded: boolean;
  rowData: any;
};
