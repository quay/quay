import {generateAvatarFromName} from './avatarUtils';

describe('generateAvatarFromName', () => {
  it('returns correct shape', () => {
    const result = generateAvatarFromName('testorg');
    expect(result).toHaveProperty('name', 'testorg');
    expect(result).toHaveProperty('hash');
    expect(result).toHaveProperty('color');
    expect(result).toHaveProperty('kind', 'generated');
  });

  it('is deterministic for same name', () => {
    const a = generateAvatarFromName('myorg');
    const b = generateAvatarFromName('myorg');
    expect(a).toEqual(b);
  });

  it('produces different hashes for different names', () => {
    const alice = generateAvatarFromName('alice');
    const bob = generateAvatarFromName('bob');
    expect(alice.hash).not.toBe(bob.hash);
  });

  it('color is a valid hex string', () => {
    const result = generateAvatarFromName('test');
    expect(result.color).toMatch(/^#[0-9a-f]{6}$/i);
  });
});
