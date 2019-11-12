import { DataFileServiceImpl } from './datafile.service.impl';
import { Mock } from 'ts-mocks';
import Spy = jasmine.Spy;


describe("DataFileServiceImpl", () => {
  var dataFileServiceImpl: DataFileServiceImpl;
  var fileReaderMock: Mock<FileReader>;
  var fileReader: FileReader;

  beforeEach(() => {
    fileReaderMock = new Mock<FileReader>();
    fileReader = fileReaderMock.Object;
    dataFileServiceImpl = new DataFileServiceImpl(() => fileReader);
  });

  describe("blobToString", () => {
    var data: any;
    var blob: Blob;

    beforeEach(() => {
      data = {hello: "world"};
      blob = new Blob([JSON.stringify(data)]);

      fileReaderMock.setup(mock => mock.readAsText).is((blob: Blob) => {
        fileReaderMock.Object.onload(<any>{target: {result: data}});
      });
    });

    it("calls file reader to read given blob", (done) => {
      dataFileServiceImpl.blobToString(blob, (result) => {
        expect((<Spy>fileReader.readAsText).calls.argsFor(0)[0]).toEqual(blob);
        done();
      });
    });

    it("calls given callback with null if file reader errors", (done) => {
      fileReaderMock.setup(mock => mock.readAsText).is((blob: Blob) => {
        fileReaderMock.Object.onerror(new Mock<ProgressEvent<FileReader>>().Object);
      });

      dataFileServiceImpl.blobToString(blob, (result) => {
        expect(result).toBe(null);
        done();
      });
    });

    it("calls given callback with null if file reader aborts", (done) => {
      fileReaderMock.setup(mock => mock.readAsText).is((blob: Blob) => {
        fileReaderMock.Object.onabort(new Mock<ProgressEvent<FileReader>>().Object);
      });

      dataFileServiceImpl.blobToString(blob, (result) => {
        expect(result).toBe(null);
        done();
      });
    });

    it("calls given callback with result when file reader successfully loads", (done) => {
      dataFileServiceImpl.blobToString(blob, (result) => {
        expect(result).toBe(data);
        done();
      });
    });
  });

  describe("arrayToString", () => {
    var blob: Blob;
    var data: any;

    beforeEach(() => {
      data = JSON.stringify({hello: "world"});
      blob = new Blob([data], {type: 'application/octet-binary'});

      fileReaderMock.setup(mock => mock.readAsText).is((blob: Blob) => {
        fileReaderMock.Object.onload(<any>{target: {result: data}});
      });
    });

    it("calls file reader to read blob created from given buffer", (done) => {
      dataFileServiceImpl.arrayToString(data, (result) => {
        expect((<Spy>fileReader.readAsText).calls.argsFor(0)[0]).toEqual(blob);
        done();
      });
    });

    it("calls given callback with null if file reader errors", (done) => {
      fileReaderMock.setup(mock => mock.readAsText).is((blob: Blob) => {
        fileReaderMock.Object.onerror(new Mock<ProgressEvent<FileReader>>().Object);
      });

      dataFileServiceImpl.arrayToString(data, (result) => {
        expect(result).toEqual(null);
        done();
      });
    });

    it("calls given callback with null if file reader aborts", (done) => {
      fileReaderMock.setup(mock => mock.readAsText).is((blob: Blob) => {
        fileReaderMock.Object.onabort(new Mock<ProgressEvent<FileReader>>().Object);
      });

      dataFileServiceImpl.arrayToString(data, (result) => {
        expect(result).toEqual(null);
        done();
      });
    });

    it("calls given callback with result when file reader successfully loads", (done) => {
      dataFileServiceImpl.arrayToString(data, (result) => {
        expect(result).toEqual(data);
        done();
      });
    });
  });

  describe("readDataArrayAsPossibleArchive", () => {
    // TODO
  });

  describe("downloadDataFileAsArrayBuffer", () => {
    // TODO
  });
});
