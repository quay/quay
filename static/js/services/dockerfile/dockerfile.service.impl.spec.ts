import { DockerfileServiceImpl, DockerfileInfoImpl } from './dockerfile.service.impl';
import { DataFileService } from '../datafile/datafile.service';
import Spy = jasmine.Spy;
import { Mock } from 'ts-mocks';


describe("DockerfileServiceImpl", () => {
  var dockerfileServiceImpl: DockerfileServiceImpl;
  var dataFileServiceMock: Mock<DataFileService>;
  var dataFileService: DataFileService;
  var configMock: any;
  var fileReaderMock: Mock<FileReader>;

  beforeEach(() => {
    dataFileServiceMock = new Mock<DataFileService>();
    dataFileService = dataFileServiceMock.Object;
    configMock = jasmine.createSpyObj('configMock', ['getDomain']);
    fileReaderMock = new Mock<FileReader>();
    dockerfileServiceImpl = new DockerfileServiceImpl(dataFileService, configMock, () => fileReaderMock.Object);
  });

  describe("getDockerfile", () => {
    var file: any;
    var invalidArchiveFile: any[];
    var validArchiveFile: any[];
    var forDataSpy: Spy;

    beforeEach(() => {
      file = "FROM quay.io/coreos/nginx:latest";
      validArchiveFile = [{name: 'Dockerfile', path: 'Dockerfile', toBlob: jasmine.createSpy('toBlobSpy').and.returnValue(file)}];
      invalidArchiveFile = [{name: 'main.exe', path: 'main.exe', toBlob: jasmine.createSpy('toBlobSpy').and.returnValue("")}];

      dataFileServiceMock.setup(mock => mock.readDataArrayAsPossibleArchive).is((buf, success, failure) => {
        failure([]);
      });

      dataFileServiceMock.setup(mock => mock.arrayToString).is((buf, callback) => callback(""));

      dataFileServiceMock.setup(mock => mock.blobToString).is((blob, callback) => callback(blob.toString()));

      forDataSpy = spyOn(DockerfileInfoImpl, "forData").and.returnValue(new DockerfileInfoImpl(file, configMock));

      fileReaderMock.setup(mock => mock.readAsArrayBuffer).is((blob: Blob) => {
        fileReaderMock.Object.onload(<any>{target: {result: file}});
      });
    });

    it("calls datafile service to read given file as possible archive file", (done) => {
      dockerfileServiceImpl.getDockerfile(file)
        .then((dockerfile: DockerfileInfoImpl) => {
          expect((<Spy>fileReaderMock.Object.readAsArrayBuffer).calls.argsFor(0)[0]).toEqual(file);
          expect(dataFileService.readDataArrayAsPossibleArchive).toHaveBeenCalled();
          done();
        })
        .catch((error: string) => {
          fail('Promise should be resolved');
          done();
        });
    });

    it("calls datafile service to convert file to string if given file is not an archive", (done) => {
      dockerfileServiceImpl.getDockerfile(file)
        .then((dockerfile: DockerfileInfoImpl) => {
          expect((<Spy>dataFileService.arrayToString).calls.argsFor(0)[0]).toEqual(file);
          done();
        })
        .catch((error: string) => {
          fail('Promise should be resolved');
          done();
        });
    });

    it("returns rejected promise if given non-archive file that is not a valid Dockerfile", (done) => {
      forDataSpy.and.returnValue(null);
      dockerfileServiceImpl.getDockerfile(file)
        .then((dockerfile: DockerfileInfoImpl) => {
          fail("Promise should be rejected");
          done();
        })
        .catch((error: string) => {
          expect(error).toEqual('File chosen is not a valid Dockerfile');
          done();
        });
    });

    it("returns resolved promise with new DockerfileInfoImpl instance if given valid Dockerfile", (done) => {
      dockerfileServiceImpl.getDockerfile(file)
        .then((dockerfile: DockerfileInfoImpl) => {
          expect(dockerfile).toBeDefined();
          done();
        })
        .catch((error: string) => {
          fail('Promise should be resolved');
          done();
        });
    });

    it("returns rejected promise if given archive file with no Dockerfile present in root directory", (done) => {
      dataFileServiceMock.setup(mock => mock.readDataArrayAsPossibleArchive).is((buf, success, failure) => {
        success(invalidArchiveFile);
      });

      dockerfileServiceImpl.getDockerfile(file)
        .then((dockerfile: DockerfileInfoImpl) => {
          fail('Promise should be rejected');
          done();
        })
        .catch((error: string) => {
          expect(error).toEqual('No Dockerfile found in root of archive');
          done();
        });
    });

    it("calls datafile service to convert blob to string if given file is an archive", (done) => {
      dataFileServiceMock.setup(mock => mock.readDataArrayAsPossibleArchive).is((buf, success, failure) => {
        success(validArchiveFile);
      });

      dockerfileServiceImpl.getDockerfile(file)
        .then((dockerfile: DockerfileInfoImpl) => {
          expect(validArchiveFile[0].toBlob).toHaveBeenCalled();
          expect((<Spy>dataFileService.blobToString).calls.argsFor(0)[0]).toEqual(validArchiveFile[0].toBlob());
          done();
        })
        .catch((error: string) => {
          fail('Promise should be resolved');
          done();
        });
    });

    it("returns rejected promise if given archive file with invalid Dockerfile", (done) => {
      forDataSpy.and.returnValue(null);
      invalidArchiveFile[0].name = 'Dockerfile';
      invalidArchiveFile[0].path = 'Dockerfile';
      dataFileServiceMock.setup(mock => mock.readDataArrayAsPossibleArchive).is((buf, success, failure) => {
        success(invalidArchiveFile);
      });

      dockerfileServiceImpl.getDockerfile(file)
        .then((dockerfile: DockerfileInfoImpl) => {
          fail('Promise should be rejected');
          done();
        })
        .catch((error: string) => {
          expect(error).toEqual('Dockerfile inside archive is not a valid Dockerfile');
          done();
        });
    });

    it("returns resolved promise of new DockerfileInfoImpl instance if given archive with valid Dockerfile", (done) => {
      dataFileServiceMock.setup(mock => mock.readDataArrayAsPossibleArchive).is((buf, success, failure) => {
        success(validArchiveFile);
      });

      dockerfileServiceImpl.getDockerfile(file)
        .then((dockerfile: DockerfileInfoImpl) => {
          expect(dockerfile).toBeDefined();
          done();
        })
        .catch((error: string) => {
          fail('Promise should be resolved');
          done();
        });
    });
  });
});


describe("DockerfileInfoImpl", () => {
  var dockerfileInfoImpl: DockerfileInfoImpl;
  var contents: string;
  var configMock: any;

  beforeEach(() => {
    contents = "";
    configMock = jasmine.createSpyObj('configMock', ['getDomain']);
    dockerfileInfoImpl = new DockerfileInfoImpl(contents, configMock);
  });

  describe("forData", () => {

    it("returns null if given contents do not contain a 'FROM' command", () => {
      expect(DockerfileInfoImpl.forData(contents, configMock)).toBe(null);
    });

    it("returns a new DockerfileInfoImpl instance if given contents are valid", () => {
      contents = "FROM quay.io/coreos/nginx";

      expect(DockerfileInfoImpl.forData(contents, configMock) instanceof DockerfileInfoImpl).toBe(true);
    });
  });

  describe("getRegistryBaseImage", () => {
    var domain: string;
    var baseImage: string;

    beforeEach(() => {
      domain = "quay.io";
      baseImage = "coreos/nginx";

      configMock.getDomain.and.returnValue(domain);
    });

    it("returns null if instance's contents do not contain a 'FROM' command", () => {
      var getBaseImageSpy: Spy = spyOn(dockerfileInfoImpl, "getBaseImage").and.returnValue(null);

      expect(dockerfileInfoImpl.getRegistryBaseImage()).toBe(null);
      expect(getBaseImageSpy).toHaveBeenCalled();
    });

    it("returns null if the domain of the instance's config does not match that of the base image", () => {
      configMock.getDomain.and.returnValue(domain);
      spyOn(dockerfileInfoImpl, "getBaseImage").and.returnValue('host.com');

      expect(dockerfileInfoImpl.getRegistryBaseImage()).toBe(null);
      expect(configMock.getDomain).toHaveBeenCalled();
    });

    it("returns the registry base image", () => {
      spyOn(dockerfileInfoImpl, "getBaseImage").and.returnValue(`${domain}/${baseImage}`);

      expect(dockerfileInfoImpl.getRegistryBaseImage()).toEqual(baseImage);
    });
  });

  describe("getBaseImage", () => {
    var host: string;
    var port: number;
    var tag: string;
    var image: string;

    beforeEach(() => {
      host = 'quay.io';
      port = 80;
      tag = 'latest';
      image = 'coreos/nginx';
    });

    it("returns null if instance's contents do not contain a 'FROM' command", () => {
      var getBaseImageAndTagSpy: Spy = spyOn(dockerfileInfoImpl, "getBaseImageAndTag").and.returnValue(null);

      expect(dockerfileInfoImpl.getBaseImage()).toBe(null);
      expect(getBaseImageAndTagSpy).toHaveBeenCalled();
    });

    it("returns the image name if in the format 'someimage'", () => {
      spyOn(dockerfileInfoImpl, "getBaseImageAndTag").and.returnValue(image);

      expect(dockerfileInfoImpl.getBaseImage()).toEqual(image);
    });

    it("returns the image name if in the format 'someimage:tag'", () => {
      spyOn(dockerfileInfoImpl, "getBaseImageAndTag").and.returnValue(`${image}:${tag}`);

      expect(dockerfileInfoImpl.getBaseImage()).toEqual(image);
    });

    it("returns the host, port, and image name if in the format 'host:port/someimage'", () => {
      spyOn(dockerfileInfoImpl, "getBaseImageAndTag").and.returnValue(`${host}:${port}/${image}`);

      expect(dockerfileInfoImpl.getBaseImage()).toEqual(`${host}:${port}/${image}`);
    });

    it("returns the host, port, and image name if in the format 'host:port/someimage:tag'", () => {
      spyOn(dockerfileInfoImpl, "getBaseImageAndTag").and.returnValue(`${host}:${port}/${image}:${tag}`);

      expect(dockerfileInfoImpl.getBaseImage()).toEqual(`${host}:${port}/${image}`);
    });
  });

  describe("getBaseImageAndTag", () => {

    it("returns null if instance's contents do not contain a 'FROM' command", () => {
      expect(dockerfileInfoImpl.getBaseImageAndTag()).toBe(null);
    });

    it("returns a string containing the base image and tag from the instance's contents", () => {
      contents = "FROM quay.io/coreos/nginx";
      dockerfileInfoImpl = new DockerfileInfoImpl(contents, configMock);
      var baseImageAndTag: string = dockerfileInfoImpl.getBaseImageAndTag();

      expect(baseImageAndTag).toEqual(contents.substring('FROM '.length, contents.length).trim());
    });

    it("handles the presence of newlines", () => {
      contents = "FROM quay.io/coreos/nginx\nRUN echo $0";
      dockerfileInfoImpl = new DockerfileInfoImpl(contents, configMock);
      var baseImageAndTag: string = dockerfileInfoImpl.getBaseImageAndTag();

      expect(baseImageAndTag).toEqual(contents.substring('FROM '.length, contents.indexOf('\n')).trim());
    });
  });
});
