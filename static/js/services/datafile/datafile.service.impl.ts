import { DataFileService } from './datafile.service';
import { Injectable, Inject } from 'ng-metadata/core';
declare const JSZip: (buf: any) => void;
declare const Zlib: any;
declare const Untar: (uint8Array: Uint8Array) => void;


@Injectable(DataFileService.name)
export class DataFileServiceImpl implements DataFileService {

  constructor(@Inject('fileReaderFactory') private fileReaderFactory: () => FileReader) {

  }

  public blobToString(blob: Blob, callback: (result: string) => void): void {
    var reader: FileReader = this.fileReaderFactory();
    reader.onload = (event: Event) => callback(event.target['result']);
    reader.onerror = (event: Event) => callback(null);
    reader.onabort = (event: Event) => callback(null);
    reader.readAsText(blob);
  }

  public arrayToString(buf: any, callback: (result: string) => void): void {
    const blob: Blob = new Blob([buf], {type: 'application/octet-binary'});
    var reader: FileReader = this.fileReaderFactory();
    reader.onload = (event: Event) => callback(event.target['result']);
    reader.onerror = (event: Event) => callback(null);
    reader.onabort = (event: Event) => callback(null);
    reader.readAsText(blob);
  }

  public readDataArrayAsPossibleArchive(buf: any,
                                        success: (result: any) => void,
                                        failure: (error: any) => void): void {
    this.tryAsZip(buf, success, () => {
      this.tryAsTarGz(buf, success, () => {
        this.tryAsTar(buf, success, failure);
      });
    });
  }

  public downloadDataFileAsArrayBuffer($scope: ng.IScope,
                                       url: string,
                                       progress: (percent: number) => void,
                                       error: () => void,
                                       loaded: (uint8array: Uint8Array) => void): void {
    var request: XMLHttpRequest = new XMLHttpRequest();
    request.open('GET', url, true);
    request.responseType = 'arraybuffer';

    request.onprogress = (e) => {
      $scope.$apply(() => {
        var percentLoaded;
        if (e.lengthComputable) {
          progress(e.loaded / e.total);
        }
      });
    };

    request.onerror = () => {
      $scope.$apply(() => {
        error();
      });
    };

    request.onload = function() {
      if (request.status == 200) {
        $scope.$apply(() => {
          var uint8array = new Uint8Array(request.response);
          loaded(uint8array);
        });
        return;
      }
    };

    request.send();
  }

  private getName(filePath: string): string {
    var parts: string[] = filePath.split('/');

    return parts[parts.length - 1];
  }

  private tryAsZip(buf: any, success: (result: any) => void, failure: (error?: any) => void): void {
    var zip = null;
    var zipFiles = null;
    try {
      zip = new JSZip(buf);
      zipFiles = zip.files;
    } catch (e) {
      failure();
      return;
    }

    var files = [];
    for (var filePath in zipFiles) {
      if (zipFiles.hasOwnProperty(filePath)) {
        files.push({
          'name': this.getName(filePath),
          'path': filePath,
          'canRead': true,
          'toBlob': (function(fp) {
            return function() {
              return new Blob([zip.file(fp).asArrayBuffer()]);
            };
          }(filePath))
        });
      }
    }

    success(files);
  }

  private tryAsTarGz(buf: any, success: (result: any) => void, failure: (error?: any) => void): void {
    var gunzip = new Zlib.Gunzip(new Uint8Array(buf));
    var plain = null;

    try {
      plain = gunzip.decompress();
    } catch (e) {
      failure();
      return;
    }

    if (plain.byteLength == 0) {
      plain = buf;
    }

    this.tryAsTar(plain, success, failure);
  }

  private tryAsTar(buf: any, success: (result: any) => void, failure: (error?: any) => void): void {
    var collapsePath = function(originalPath) {
      // Tar files can contain entries of the form './', so we need to collapse
      // those paths down.
      var parts = originalPath.split('/');
      for (var i = parts.length - 1; i >= 0; i--) {
        var part = parts[i];
        if (part == '.') {
          parts.splice(i, 1);
        }
      }
      return parts.join('/');
    };

    try {
      var handler = new Untar(new Uint8Array(buf));
      handler.process((status, read, files, err) => {
        switch (status) {
          case 'error':
            failure(err);
            break;

          case 'done':
            var processed = [];
            for (var i = 0; i < files.length; ++i) {
              var currentFile = files[i];
              var path = collapsePath(currentFile.meta.filename);

              if (path == '' || path == 'pax_global_header') { continue; }

              processed.push({
                'name': this.getName(path),
                'path': path,
                'canRead': true,
                'toBlob': (function(file) {
                  return function() {
                    return new Blob([file.buffer], {type: 'application/octet-binary'});
                  };
                }(currentFile))
              });
            }
            success(processed);
            break;
        }
      });
    } catch (e) {
      failure();
    }
  }
}
