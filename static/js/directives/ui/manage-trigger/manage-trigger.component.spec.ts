import { ManageTriggerComponent } from './manage-trigger.component';
import { Local, Trigger, Repository } from '../../../types/common.types';
import { ViewArray } from '../../../services/view-array/view-array';
import { ContextChangeEvent } from '../context-path-select/context-path-select.component';
import { PathChangeEvent } from '../dockerfile-path-select/dockerfile-path-select.component';
import { Mock } from 'ts-mocks';
import Spy = jasmine.Spy;


describe("ManageTriggerComponent", () => {
  var component: ManageTriggerComponent;
  var apiServiceMock: Mock<any>;
  var tableServiceMock: Mock<any>;
  var triggerServiceMock: Mock<any>;
  var rolesServiceMock: Mock<any>;
  var keyServiceMock: Mock<any>;
  var documentationServiceMock: Mock<any>;
  var repository: any;
  var $scopeMock: Mock<ng.IScope>;

  beforeEach(() => {
    apiServiceMock = new Mock<any>();
    tableServiceMock = new Mock<any>();
    triggerServiceMock = new Mock<any>();
    rolesServiceMock = new Mock<any>();
    keyServiceMock = new Mock<any>();
    $scopeMock = new Mock<ng.IScope>();
    component = new ManageTriggerComponent(apiServiceMock.Object,
      tableServiceMock.Object,
      triggerServiceMock.Object,
      rolesServiceMock.Object,
      keyServiceMock.Object,
      documentationServiceMock.Object,
      $scopeMock.Object);
    component.repository = { namespace: "someuser", name: "somerepo" };
    component.trigger = { id: "2cac6317-754e-47d4-88d3-2a50b3f09ee3", service: "github" };
  });

  describe("ngOnChanges", () => {

    beforeEach(() => {
      apiServiceMock.setup(mock => mock.listTriggerBuildSourceNamespaces).is(() => Promise.resolve({}));
      apiServiceMock.setup(mock => mock.errorDisplay).is((message) => null);
      $scopeMock.setup(mock => mock.$watch).is((val, callback) => null);
    });

    it("sets default values for config and selected namespace", () => {
      component.ngOnChanges({});

      expect(component.config).toEqual({});
      expect(component.local.selectedNamespace).toBe(null);
    });
  });

  describe("checkBuildSource", () => {

    it("sets selected repository full name if given build source matches regex pattern", () => {
      const buildSource: string = "git@somegithost.net:user/repo.git";
      component.checkBuildSource(buildSource);

      expect(component.local.selectedRepository.full_name).toEqual(buildSource);
    });

    it("sets selected repository full name to null if given build source does not match regex pattern", () => {
      const buildSource: string = "a_randomstring";
      component.checkBuildSource(buildSource);

      expect(component.local.selectedRepository.full_name).toBe(null);
    });
  });

  describe("getTriggerIcon", () => {

    beforeEach(() => {
      triggerServiceMock.setup(mock => mock.getIcon).is((service: any) => null);
    });

    it("calls trigger service to get icon", () => {
      const icon: any = component.getTriggerIcon();

      expect((<Spy>triggerServiceMock.Object.getIcon).calls.argsFor(0)[0]).toEqual(component.trigger.service);
    });
  });

  describe("checkDockerfilePath", () => {
    var event: PathChangeEvent;

    beforeEach(() => {
      event = { path: '/Dockerfile', isValid: true };
      component.local.selectedRepository = { name: "", full_name: "someorg/somerepo" };
      component.local.dockerContext = '/';
      component.local.dockerfileLocations = { contextMap: {} };
      spyOn(component, "analyzeDockerfilePath").and.returnValue(null);
    });

    it("sets local Dockerfile path and validity to given event values", () => {
      component.checkDockerfilePath(event);

      expect(component.local.hasValidDockerfilePath).toEqual(event.isValid);
      expect(component.local.dockerfilePath).toEqual(event.path);
    });

    it("sets local Dockerfile contexts if present in local Dockerfile locations", () => {
      component.local.dockerfileLocations.contextMap[event.path] = ['/', '/dir'];
      component.checkDockerfilePath(event);

      expect(component.local.contexts).toEqual(component.local.dockerfileLocations.contextMap[event.path]);
    });

    it("sets local Dockerfile contexts to empty array if given path not present in local Dockerfile locations", () => {
      component.checkDockerfilePath(event);

      expect(component.local.contexts).toEqual([]);
    });

    it("calls component method to analyze new Dockerfile path", () => {
      component.checkDockerfilePath(event);

      expect((<Spy>component.analyzeDockerfilePath).calls.argsFor(0)[0]).toEqual(component.local.selectedRepository);
      expect((<Spy>component.analyzeDockerfilePath).calls.argsFor(0)[1]).toEqual(event.path);
      expect((<Spy>component.analyzeDockerfilePath).calls.argsFor(0)[2]).toEqual(component.local.dockerContext);
    });
  });

  describe("checkBuildContext", () => {
    var event: ContextChangeEvent;

    beforeEach(() => {
      event = { contextDir: '/', isValid: true };
    });
  });

  describe("analyzeDockerfilePath", () => {
    var selectedRepository: Repository;
    var path: string;
    var context: string;
    var robots: { robots: { [key: string]: any }[] };
    var analysis: { [key: string]: any };
    var orderedRobots: Mock<ViewArray>;

    beforeEach(() => {
      selectedRepository = { name: "", full_name: "someorg/somerepo" };
      path = "/Dockerfile";
      context = "/";
      robots = { robots: [{ name: 'robot' }] };
      analysis = { 'publicbase': true, robots: robots.robots };
      orderedRobots = new Mock<ViewArray>();
      apiServiceMock.setup(mock => mock.analyzeBuildTrigger).is((data, params) => Promise.resolve(analysis));
      apiServiceMock.setup(mock => mock.getRobots).is((user, arg, params) => Promise.resolve(robots));
      apiServiceMock.setup(mock => mock.errorDisplay).is((message) => null);
      tableServiceMock.setup(mock => mock.buildOrderedItems).is((items, options, filterFields, numericFields) => orderedRobots.Object);
    });

    it("does nothing if given invalid Git repository", (done) => {
      const invalidRepositories: Repository[] = [null];
      invalidRepositories.forEach((repo, index) => {
        component.analyzeDockerfilePath(repo, path, context);

        expect((<Spy>apiServiceMock.Object.analyzeBuildTrigger)).not.toHaveBeenCalled();

        if (index == invalidRepositories.length - 1) {
          done();
        }
      });
    });

    it("uses default values for Dockerfile path and context if not given", (done) => {
      const spy: Spy = <Spy>apiServiceMock.Object.analyzeBuildTrigger;
      component.analyzeDockerfilePath(selectedRepository);

      setTimeout(() => {
        expect(spy.calls.argsFor(0)[0]['config']['build_source']).toEqual(selectedRepository.full_name);
        expect(spy.calls.argsFor(0)[0]['config']['dockerfile_path']).toEqual('Dockerfile');
        expect(spy.calls.argsFor(0)[0]['config']['context']).toEqual('/');
        expect(spy.calls.argsFor(0)[1]['repository']).toEqual(`${component.repository.namespace}/${component.repository.name}`);
        expect(spy.calls.argsFor(0)[1]['trigger_uuid']).toEqual(component.trigger.id);
        done();
      }, 10);
    });

    it("calls API service to analyze build trigger config with given values", (done) => {
      const spy: Spy = <Spy>apiServiceMock.Object.analyzeBuildTrigger;
      component.analyzeDockerfilePath(selectedRepository, path, context);

      setTimeout(() => {
        expect(spy.calls.argsFor(0)[0]['config']['build_source']).toEqual(selectedRepository.full_name);
        expect(spy.calls.argsFor(0)[0]['config']['dockerfile_path']).toEqual(path.substr(1));
        expect(spy.calls.argsFor(0)[0]['config']['context']).toEqual(context);
        expect(spy.calls.argsFor(0)[1]['repository']).toEqual(`${component.repository.namespace}/${component.repository.name}`);
        expect(spy.calls.argsFor(0)[1]['trigger_uuid']).toEqual(component.trigger.id);
        done();
      }, 10);
    });

    it("calls API service to display error if API service's trigger analysis fails", (done) => {
      apiServiceMock.setup(mock => mock.analyzeBuildTrigger).is((data, params) => Promise.reject("Error"));
      component.analyzeDockerfilePath(selectedRepository, path, context);

      setTimeout(() => {
        expect((<Spy>apiServiceMock.Object.errorDisplay).calls.argsFor(0)[0]).toEqual('Could not analyze trigger');
        done();
      }, 10);
    });

    it("updates component trigger analysis with successful trigger analysis response", (done) => {
      component.analyzeDockerfilePath(selectedRepository, path, context);

      setTimeout(() => {
        expect(component.local.triggerAnalysis).toEqual(analysis);
        done();
      }, 10);
    });
  });

  describe("createTrigger", () => {

    beforeEach(() => {
      component.local.selectedRepository = new Mock<Repository>().Object;
      component.local.selectedRepository.full_name = "someorg/some-repository";
      component.local.dockerfilePath = "/Dockerfile";
      component.local.dockerContext = "/";
      component.local.triggerOptions = {};
      component.local.triggerAnalysis = {};
      rolesServiceMock.setup(mock => mock.setRepositoryRole).is((repo, role, entityKind, entityName, callback) => {
        callback();
      });
    });

    it("does not call roles service if robot is required but robot is not selected", (done) => {
      component.local.triggerAnalysis = { status: 'requiresrobot', name: 'privatebase', namespace: 'someorg' };
      component.local.robotAccount = null;
      component.activateTrigger.subscribe((event: { config: any, pull_robot: any }) => {
        expect((<Spy>rolesServiceMock.Object.setRepositoryRole)).not.toHaveBeenCalled();
        done();
      });

      component.createTrigger();
    });

    it("calls roles service to grant read access to selected robot if robot is required and cannot read", (done) => {
      component.local.triggerAnalysis = { status: 'requiresrobot', name: 'privatebase', namespace: 'someorg' };
      component.local.robotAccount = { can_read: false, is_robot: true, kind: 'user', name: 'test-robot' };
      component.activateTrigger.subscribe((event: { config: any, pull_robot: any }) => {
        expect((<Spy>rolesServiceMock.Object.setRepositoryRole).calls.argsFor(0)[0]).toEqual({
          name: component.local.triggerAnalysis.name,
          namespace: component.local.triggerAnalysis.namespace,
        });
        expect((<Spy>rolesServiceMock.Object.setRepositoryRole).calls.argsFor(0)[1]).toEqual('read');
        expect((<Spy>rolesServiceMock.Object.setRepositoryRole).calls.argsFor(0)[2]).toEqual('robot');
        done();
      });

      component.createTrigger();
    });

    it("does not call roles service if robot is required but already has read access", (done) => {
      component.local.triggerAnalysis = { status: 'requiresrobot', name: 'privatebase', namespace: 'someorg' };
      component.local.robotAccount = { can_read: true, is_robot: true, kind: 'user', name: 'test-robot' };
      component.activateTrigger.subscribe((event: { config: any, pull_robot: any }) => {
        expect((<Spy>rolesServiceMock.Object.setRepositoryRole)).not.toHaveBeenCalled();
        done();
      });

      component.createTrigger();
    });

    it("does not call roles service if robot is not required", (done) => {
      component.local.triggerAnalysis = { status: 'publicbase', name: 'publicrepo', namespace: 'someorg' };
      component.activateTrigger.subscribe((event: { config: any, pull_robot: any }) => {
        expect((<Spy>rolesServiceMock.Object.setRepositoryRole)).not.toHaveBeenCalled();
        done();
      });

      component.createTrigger();
    });

    it("emits output event with config and pull robot", (done) => {
      component.activateTrigger.subscribe((event: { config: any, pull_robot: any }) => {
        expect(event.config.build_source).toEqual(component.local.selectedRepository.full_name);
        expect(event.config.dockerfile_path).toEqual(component.local.dockerfilePath);
        expect(event.config.context).toEqual(component.local.dockerContext);
        done();
      });

      component.createTrigger();
    });
  });
});
