import { DockerfileService, DockerfileInfo } from './dockerfile.service';
import { Injectable, Inject } from 'ng-metadata/core';
import { DataFileService } from '../datafile/datafile.service';


@Injectable(DockerfileService.name)
export class DockerfileServiceImpl implements DockerfileService {

  constructor(@Inject(DataFileService.name) private DataFileService: DataFileService,
              @Inject('Config') private Config: any,
              @Inject('fileReaderFactory') private fileReaderFactory: () => FileReader) {

  }

  public getDockerfile(file: any): Promise<DockerfileInfoImpl | string> {
    return new Promise((resolve, reject) => {
      var reader: FileReader = this.fileReaderFactory();
      reader.onload = (event: any) => {
        this.DataFileService.readDataArrayAsPossibleArchive(event.target.result,
          (files: any[]) => {
            if (files.length > 0) {
              this.processFiles(files)
                .then((dockerfileInfo: DockerfileInfoImpl) => resolve(dockerfileInfo))
                .catch((error: string) => reject(error));
            }
            // Not an archive. Read directly as a single file.
            else {
              this.processFile(event.target.result)
                .then((dockerfileInfo: DockerfileInfoImpl) => resolve(dockerfileInfo))
                .catch((error: string) => reject(error));
            }
          },
          () => {
            // Not an archive. Read directly as a single file.
            this.processFile(event.target.result)
              .then((dockerfileInfo: DockerfileInfoImpl) => resolve(dockerfileInfo))
              .catch((error: string) => reject(error));
          });
      };

      reader.onerror = (event: any) => reject(event);
      reader.readAsArrayBuffer(file);
    });
  }

  private processFile(dataArray: any): Promise<DockerfileInfoImpl | string> {
    return new Promise((resolve, reject) => {
      this.DataFileService.arrayToString(dataArray, (contents: string) => {
        var result: DockerfileInfoImpl | null = DockerfileInfoImpl.forData(contents, this.Config);
        if (result == null) {
          reject('File chosen is not a valid Dockerfile');
        }
        else {
          resolve(result);
        }
      });
    });
  }

  private processFiles(files: any[]): Promise<DockerfileInfoImpl | string> {
    return new Promise((resolve, reject) => {
      var found: boolean = false;
      files.forEach((file) => {
        if (file['path'] == 'Dockerfile' || file['path'] == '/Dockerfile') {
          this.DataFileService.blobToString(file.toBlob(), (contents: string) => {
            var result: DockerfileInfoImpl | null = DockerfileInfoImpl.forData(contents, this.Config);
            if (result == null) {
              reject('Dockerfile inside archive is not a valid Dockerfile');
            }
            else {
              resolve(result);
            }
          });
          found = true;
        }
      });

      if (!found) {
        reject('No Dockerfile found in root of archive');
      }
    });
  }
}


export class DockerfileInfoImpl implements DockerfileInfo {

  constructor(private contents: string, private config: any) {

  }

  public static forData(contents: string, config: any): DockerfileInfoImpl | null {
    var dockerfileInfo: DockerfileInfoImpl = null;
    if (contents.indexOf('FROM ') != -1) {
      dockerfileInfo = new DockerfileInfoImpl(contents, config);
    }

    return dockerfileInfo;
  }

  public getRegistryBaseImage(): string | null {
    var baseImage = this.getBaseImage();
    if (!baseImage) {
      return null;
    }

    if (baseImage.indexOf(`${this.config.getDomain()}/`) != 0) {
      return null;
    }

    return baseImage.substring(<number>this.config.getDomain().length + 1);
  }

  public getBaseImage(): string | null {
    const imageAndTag = this.getBaseImageAndTag();
    if (!imageAndTag) {
      return null;
    }

    // Note, we have to handle a few different cases here:
    // 1) someimage
    // 2) someimage:tag
    // 3) host:port/someimage
    // 4) host:port/someimage:tag
    const lastIndex: number = imageAndTag.lastIndexOf(':');
    if (lastIndex == -1) {
      return imageAndTag;
    }

    // Otherwise, check if there is a / in the portion after the split point. If so,
    // then the latter is part of the path (and not a tag).
    const afterColon: string = imageAndTag.substring(lastIndex + 1);
    if (afterColon.indexOf('/') != -1) {
      return imageAndTag;
    }

    return imageAndTag.substring(0, lastIndex);
  }

  public getBaseImageAndTag(): string | null {
    var baseImageAndTag: string = null;

    const fromIndex: number = this.contents.indexOf('FROM ');
    if (fromIndex != -1) {
      var newlineIndex: number = this.contents.indexOf('\n', fromIndex);
      if (newlineIndex == -1) {
        newlineIndex = this.contents.length;
      }

      baseImageAndTag = this.contents.substring(fromIndex + 'FROM '.length, newlineIndex).trim();
    }

    return baseImageAndTag;
  }
}
