import { AvatarServiceImpl } from './avatar.service.impl';


describe("AvatarServiceImpl", () => {
  var avatarServiceImpl: AvatarServiceImpl;
  var configMock: any;
  var md5Mock: any;

  beforeEach(() => {
    configMock = {AVATAR_KIND: 'local'};
    md5Mock = jasmine.createSpyObj('md5Mock', ['createHash']);
    avatarServiceImpl = new AvatarServiceImpl(configMock, md5Mock);
  });

  describe("getAvatar", () => {
    var hash: string;

    beforeEach(() => {
      hash = "a1b2c3d4e5f6";
    });

    it("returns a local avatar URL if given config has avatar kind set to local", () => {
      var avatarURL: string = avatarServiceImpl.getAvatar(hash);

      expect(avatarURL).toEqual(`/avatar/${hash}?size=16`);
    });

    it("returns a Gravatar URL if given config has avatar kind set to Gravatar", () => {
      configMock['AVATAR_KIND'] = 'gravatar';
      var avatarURL: string = avatarServiceImpl.getAvatar(hash);

      expect(avatarURL).toEqual(`//www.gravatar.com/avatar/${hash}?d=404&size=16`);
    });

    it("uses 16 as default size query parameter if not provided", () => {
      var size: number = 16;
      var avatarURL: string = avatarServiceImpl.getAvatar(hash);

      expect(avatarURL).toEqual(`/avatar/${hash}?size=${size}`);
    });

    it("uses 404 as default not found query parameter for Gravatar URL if not provided", () => {
      configMock['AVATAR_KIND'] = 'gravatar';
      var notFound: string = '404';
      var avatarURL: string = avatarServiceImpl.getAvatar(hash);

      expect(avatarURL).toEqual(`//www.gravatar.com/avatar/${hash}?d=${notFound}&size=16`);
    });
  });

  describe("computeHash", () => {
    var email: string;
    var name: string;
    var expectedHash: string;

    beforeEach(() => {
      email = "some_example@gmail.com";
      name = "example";
      expectedHash = "a1b2c3d4e5f6";
      md5Mock.createHash = jasmine.createSpy('createHashSpy').and.returnValue(expectedHash);
    });

    it("returns hash from cache if it exists", () => {
      // Call once to set the cache
      avatarServiceImpl.computeHash(email, name);
      md5Mock.createHash.calls.reset();
      avatarServiceImpl.computeHash(email, name);

      expect(md5Mock.createHash).not.toHaveBeenCalled();
    });

    it("calls MD5 service to create hash using given email if cache is not set", () => {
      avatarServiceImpl.computeHash(email, name);

      expect(md5Mock.createHash.calls.argsFor(0)[0]).toEqual(email.toString().toLowerCase());
    });

    it("adds first character of given name to hash if config has avatar kind set to local", () => {
      var hash: string = avatarServiceImpl.computeHash(email, name);

      expect(hash[0]).toEqual(name[0]);
    });

    it("adds first character of given email to hash if config has avatar kind set to local and not given name", () => {
      var hash: string = avatarServiceImpl.computeHash(email);

      expect(hash[0]).toEqual(email[0]);
    });

    it("adds nothing to hash if config avatar kind is not set to local", () => {
      configMock['AVATAR_KIND'] = 'gravatar';
      var hash: string = avatarServiceImpl.computeHash(email);

      expect(hash).toEqual(expectedHash);
    });
  });
});