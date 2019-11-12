import { Mock } from 'ts-mocks';
import { CorTableComponent, CorTableOptions } from './cor-table.component';
import { CorTableColumn } from './cor-table-col.component';
import { SimpleChanges } from 'ng-metadata/core';
import { ViewArray } from '../../../services/view-array/view-array';
import Spy = jasmine.Spy;


describe("CorTableComponent", () => {
  var component: CorTableComponent;
  var tableServiceMock: Mock<any>;
  var tableData: any[];
  var columnMocks: Mock<CorTableColumn>[];
  var orderedDataMock: Mock<ViewArray>;

  beforeEach(() => {
    orderedDataMock = new Mock<ViewArray>();
    orderedDataMock.setup(mock => mock.visibleEntries).is([]);
    tableServiceMock = new Mock<any>();
    tableServiceMock.setup(mock => mock.buildOrderedItems)
      .is((items, options, filterFields, numericFields, extrafilter?) => orderedDataMock.Object);

    tableData = [
      {name: "apple",  last_modified: 1496068383000, version: "1.0.0"},
      {name: "pear",   last_modified: 1496068383001, version: "1.1.0"},
      {name: "orange", last_modified: 1496068383002, version: "1.0.0"},
      {name: "banana", last_modified: 1496068383000, version: "2.0.0"},
    ];

    columnMocks = Object.keys(tableData[0])
      .map((key, index) => {
        const col = new Mock<CorTableColumn>();
        col.setup(mock => mock.isNumeric).is(() => index == 1 ? true : false);
        col.setup(mock => mock.processColumnForOrdered).is((value) => "dummy");
        col.setup(mock => mock.datafield).is(key);

        return col;
      });

    component = new CorTableComponent(tableServiceMock.Object);
    component.tableData = tableData;
    component.filterFields = ['name', 'version'];
    component.compact = false;
    component.tableItemTitle = "fruits";
    component.maxDisplayCount = 10;
    // Add columns
    columnMocks.forEach(colMock => component.addColumn(colMock.Object));
    (<Spy>tableServiceMock.Object.buildOrderedItems).calls.reset();
  });

  describe("constructor", () => {

    it("sets table options", () => {
      expect(component.options.filter).toEqual('');
      expect(component.options.reverse).toBe(false);
      expect(component.options.predicate).toEqual('');
      expect(component.options.page).toEqual(0);
    });
  });

  describe("ngOnChanges", () => {
    var changes: SimpleChanges;

    it("calls table service to build ordered items if table data is changed", () => {
      changes = {tableData: {currentValue: [], previousValue: [], isFirstChange: () => false}};
      component.ngOnChanges(changes);

      expect((<Spy>tableServiceMock.Object.buildOrderedItems)).toHaveBeenCalled();
    });

    it("passes processed table data to table service", () => {
      changes = {tableData: {currentValue: [], previousValue: [], isFirstChange: () => false}};
      component.tableData = changes['tableData'].currentValue;
      component.ngOnChanges(changes);

      expect((<Spy>tableServiceMock.Object.buildOrderedItems).calls.argsFor(0)[0]).not.toEqual(tableData);
    });

    it("passes options to table service", () => {
      changes = {tableData: {currentValue: [], previousValue: [], isFirstChange: () => false}};
      component.ngOnChanges(changes);

      expect((<Spy>tableServiceMock.Object.buildOrderedItems).calls.argsFor(0)[1]).toEqual(component.options);
    });

    it("passes filter fields to table service", () => {
      changes = {tableData: {currentValue: [], previousValue: [], isFirstChange: () => false}};
      component.ngOnChanges(changes);

      expect((<Spy>tableServiceMock.Object.buildOrderedItems).calls.argsFor(0)[2]).toEqual(component.filterFields);
    });

    it("passes numeric fields to table service", () => {
      changes = {tableData: {currentValue: [], previousValue: [], isFirstChange: () => false}};
      component.ngOnChanges(changes);

      const expectedNumericCols: string[] = columnMocks.filter(colMock => colMock.Object.isNumeric())
        .map(colMock => colMock.Object.datafield);

      expect((<Spy>tableServiceMock.Object.buildOrderedItems).calls.argsFor(0)[3]).toEqual(expectedNumericCols);
    });

    it("resets to first page if table data is changed", () => {
      component.options.page = 1;
      changes = {tableData: {currentValue: [], previousValue: [], isFirstChange: () => false}};
      component.ngOnChanges(changes);

      expect(component.options.page).toEqual(0);
    });
  });

  describe("addColumn", () => {
    var columnMock: Mock<CorTableColumn>;

    beforeEach(() => {
      columnMock = new Mock<CorTableColumn>();
      columnMock.setup(mock => mock.isNumeric).is(() => false);
    });

    it("calls table service to build ordered items with new column", () => {
      component.addColumn(columnMock.Object);

      expect((<Spy>tableServiceMock.Object.buildOrderedItems)).toHaveBeenCalled();
    });
  });
});
