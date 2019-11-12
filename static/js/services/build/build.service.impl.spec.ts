import { BuildServiceImpl } from './build.service.impl';


describe("BuildServiceImpl", () => {
  var buildServiceImpl: BuildServiceImpl;
  var build: {phase: string};

  beforeEach(() => {
    buildServiceImpl = new BuildServiceImpl();
    build = {phase: ""};
  });

  describe("isActive", () => {
    var phases: string[];

    beforeEach(() => {
      phases = ['complete', 'error', 'expired', 'cancelled'];
    });

    it("returns false if given build's phase matches an inactive phase", () => {
      phases.forEach((phase: string) => {
        build.phase = phase;

        expect(buildServiceImpl.isActive(build)).toBe(false);
      });
    });

    it("returns true if given build's phase does not match inactive phases", () => {
      build.phase = 'initializing';

      expect(buildServiceImpl.isActive(build)).toBe(true);
    });
  });

  describe("getBuildMessage", () => {
    var buildMessages: {phase?: string, message: string}[];

    beforeEach(() => {
      buildMessages = [
        {message: ""},
        {phase: null, message: ""},
        {phase: 'cannot_load', message: 'Cannot load build status'},
        {phase: 'starting', message: 'Starting Dockerfile build'},
        {phase: 'initializing', message: 'Starting Dockerfile build'},
        {phase: 'waiting', message: 'Waiting for available build worker'},
        {phase: 'unpacking', message: 'Unpacking build package'},
        {phase: 'pulling', message: 'Pulling base image'},
        {phase: 'building', message: 'Building image from Dockerfile'},
        {phase: 'checking-cache', message: 'Looking up cached images'},
        {phase: 'priming-cache', message: 'Priming cache for build'},
        {phase: 'build-scheduled', message: 'Preparing build node'},
        {phase: 'pushing', message: 'Pushing image built from Dockerfile'},
        {phase: 'complete', message: 'Dockerfile build completed and pushed'},
        {phase: 'error', message: 'Dockerfile build failed'},
        {phase: 'expired', message: 'Build did not complete after 3 attempts. Re-submit this build to try again.'},
        {phase: 'internalerror', message: 'An internal system error occurred while building; the build will be retried in the next few minutes.'},
        {phase: 'cancelled', message: 'This build was previously cancelled.'},
      ];
    });

    it("returns the correct message for the given phase", () => {
      buildMessages.forEach((buildMessage) => {
        expect(buildServiceImpl.getBuildMessage(buildMessage.phase)).toEqual(buildMessage.message, buildMessage);
      });
    });

    it("throws an error if given phase is not supported", () => {
      var phase: string = "not-a-phase";

      try {
        buildServiceImpl.getBuildMessage(phase);
        fail("Should throw error");
      } catch (error) {
        expect(error.message).toEqual(`Invalid build phase: ${phase.toString()}`);
      }
    });
  });
});