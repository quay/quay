/**
 * Service which provides helper methods for downloading a data file from a URL, and extracting
 * its contents as .tar, .tar.gz, or .zip file. Note that this service depends on external
 * library code in the lib/ directory:
 *  - jszip.min.js
 *  - Blob.js
 *  - zlib.js
 */
export abstract class DataFileService {

  /**
   * Convert a blob to a string.
   * @param blob The blob to convert.
   * @param callback The success callback given converted blob.
   */
  public abstract blobToString(blob: Blob, callback: (result: string) => void): void;

  /**
   * Convert array to string.
   * @param buf The array buffer to convert.
   * @param callback The success callback given converted array buffer.
   */
  public abstract arrayToString(buf: any, callback: (result: string) => void): void;

  /**
   * Determine if a given data array is an archive file.
   * @param buf The data array to check.
   * @param success The success callback if the given array is an archive file, given the file contents.
   * @param failure The failure callback if the given array is not an archive file, given the error message.
   */
  public abstract readDataArrayAsPossibleArchive(buf: any,
                                                 success: (result: any) => void,
                                                 failure: (error: any) => void): void;

  /**
   * Download a file into an array buffer while tracking progress.
   * @param $scope An AngularJS $scope instance.
   * @param url The URL of the file to be downloaded.
   * @param progress The callback for download progress.
   * @param error The error callback.
   * @param loaded The success callback given the downloaded array buffer.
   */
  public abstract downloadDataFileAsArrayBuffer($scope: ng.IScope,
                                                url: string,
                                                progress: (percent: number) => void,
                                                error: () => void,
                                                loaded: (uint8array: Uint8Array) => void): void;
}
