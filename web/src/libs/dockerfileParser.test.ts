import {getRegistryBaseImage} from './dockerfileParser';

describe('getRegistryBaseImage', () => {
  it('extracts image from matching domain', () => {
    expect(getRegistryBaseImage('FROM quay.io/myorg/myrepo', 'quay.io')).toBe(
      'myorg/myrepo',
    );
  });

  it('strips tag from image reference', () => {
    expect(
      getRegistryBaseImage('FROM quay.io/myorg/myrepo:latest', 'quay.io'),
    ).toBe('myorg/myrepo');
  });

  it('handles host:port domain', () => {
    expect(
      getRegistryBaseImage('FROM localhost:5000/myimage', 'localhost:5000'),
    ).toBe('myimage');
  });

  it('handles host:port with tag', () => {
    expect(
      getRegistryBaseImage('FROM localhost:5000/myimage:v1', 'localhost:5000'),
    ).toBe('myimage');
  });

  it('returns null when domain does not match', () => {
    expect(
      getRegistryBaseImage('FROM docker.io/library/nginx', 'quay.io'),
    ).toBeNull();
  });

  it('returns null when no FROM instruction', () => {
    expect(getRegistryBaseImage('RUN echo hello', 'quay.io')).toBeNull();
  });

  it('parses FROM not on first line', () => {
    const dockerfile = '# comment\nFROM quay.io/org/repo\nRUN echo hello';
    expect(getRegistryBaseImage(dockerfile, 'quay.io')).toBe('org/repo');
  });

  it('returns null for simple image without domain', () => {
    expect(getRegistryBaseImage('FROM ubuntu', 'quay.io')).toBeNull();
  });
});
