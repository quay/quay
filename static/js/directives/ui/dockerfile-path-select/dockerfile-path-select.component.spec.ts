import { DockerfilePathSelectComponent, PathChangeEvent } from './dockerfile-path-select.component';


describe("DockerfilePathSelectComponent", () => {
  var component: DockerfilePathSelectComponent;
  var currentPath: string;
  var isValidPath: boolean;
  var paths: string[];
  var supportsFullListing: boolean;

  beforeEach(() => {
    component = new DockerfilePathSelectComponent();
    currentPath = '/';
    isValidPath = false;
    paths = ['/'];
    supportsFullListing = true;
    component.currentPath = currentPath;
    component.isValidPath = isValidPath;
    component.paths = paths;
    component.supportsFullListing = supportsFullListing;
  });

  describe("ngOnChanges", () => {

    it("sets valid path flag to true if current path is valid", () => {
      component.ngOnChanges({});

      expect(component.isValidPath).toBe(true);
    });

    it("sets valid path flag to false if current path is invalid", () => {
      component.currentPath = "asdfdsf";
      component.ngOnChanges({});

      expect(component.isValidPath).toBe(false);
    });
  });

  describe("setPath", () => {
    var newPath: string;

    beforeEach(() => {
      newPath = '/conf';
    });

    it("sets current path to given path", () => {
      component.setPath(newPath);

      expect(component.currentPath).toEqual(newPath);
    });

    it("sets valid path flag to true if given path is valid", () => {
      component.setPath(newPath);

      expect(component.isValidPath).toBe(true);
    });

    it("sets valid path flag to false if given path is invalid", () => {
      component.setPath("asdfsadfs");

      expect(component.isValidPath).toBe(false);
    });

    it("emits output event indicating Dockerfile path has changed", (done) => {
      component.pathChanged.subscribe((event: PathChangeEvent) => {
        expect(event.path).toEqual(newPath);
        expect(event.isValid).toBe(component.isValidPath);
        done();
      });

      component.setPath(newPath);
    });
  });

  describe("setCurrentPath", () => {
    var newPath: string;

    beforeEach(() => {
      newPath = '/conf';
    });

    it("sets current path to given path", () => {
      component.setSelectedPath(newPath);

      expect(component.currentPath).toEqual(newPath);
    });

    it("sets valid path flag to true if given path is valid", () => {
      component.setSelectedPath(newPath);

      expect(component.isValidPath).toBe(true);
    });

    it("sets valid path flag to false if given path is invalid", () => {
      component.setSelectedPath("a;lskjdf;ldsa");

      expect(component.isValidPath).toBe(false);
    });

    it("emits output event indicating Dockerfile path has changed", (done) => {
      component.pathChanged.subscribe((event: PathChangeEvent) => {
        expect(event.path).toEqual(newPath);
        expect(event.isValid).toBe(component.isValidPath);
        done();
      });

      component.setSelectedPath(newPath);
    });
  });
});
