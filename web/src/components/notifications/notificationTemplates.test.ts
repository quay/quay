import {getNotificationLink} from './notificationTemplates';

describe('getNotificationLink', () => {
  const repository = 'myorg/myrepo';
  const repositoryPage = '/repository/myorg/myrepo';

  it('links repo_push with one updated tag to the tag', () => {
    expect(
      getNotificationLink({
        kind: 'repo_push',
        metadata: {repository, updated_tags: ['latest']},
      }),
    ).toBe(`${repositoryPage}/tag/latest`);
  });

  it('links repo_push with several updated tags to the tag history', () => {
    expect(
      getNotificationLink({
        kind: 'repo_push',
        metadata: {repository, updated_tags: ['latest', 'v1']},
      }),
    ).toBe(`${repositoryPage}?tab=history`);
  });

  it('links repo_push without updated tags to the repository', () => {
    expect(
      getNotificationLink({kind: 'repo_push', metadata: {repository}}),
    ).toBe(repositoryPage);
  });

  it('links vulnerability_found to the first tag security report', () => {
    expect(
      getNotificationLink({
        kind: 'vulnerability_found',
        metadata: {repository, tags: ['v1', 'latest']},
      }),
    ).toBe(`${repositoryPage}/tag/v1?tab=securityreport`);
  });

  it.each([
    ['without tags', {}],
    ['for an untagged manifest', {tags: ['sha256:abc']}],
  ])('links vulnerability_found %s to the tags tab', (_, extra) => {
    expect(
      getNotificationLink({
        kind: 'vulnerability_found',
        metadata: {repository, ...extra},
      }),
    ).toBe(`${repositoryPage}?tab=tags`);
  });

  it('links repo_image_expiry with one tag to the tag', () => {
    expect(
      getNotificationLink({
        kind: 'repo_image_expiry',
        metadata: {repository, tags: ['old']},
      }),
    ).toBe(`${repositoryPage}/tag/old`);
  });

  it.each([
    ['several tags', {tags: ['old', 'older']}],
    ['no tags', {}],
  ])('links repo_image_expiry with %s to the tags tab', (_, extra) => {
    expect(
      getNotificationLink({
        kind: 'repo_image_expiry',
        metadata: {repository, ...extra},
      }),
    ).toBe(`${repositoryPage}?tab=tags`);
  });

  it.each([
    'repo_mirror_sync_started',
    'repo_mirror_sync_success',
    'repo_mirror_sync_failed',
  ])('links %s to the mirroring tab', (kind) => {
    expect(getNotificationLink({kind, metadata: {repository}})).toBe(
      `${repositoryPage}?tab=mirroring`,
    );
  });

  it.each([
    'build_queued',
    'build_start',
    'build_success',
    'build_failure',
    'build_cancelled',
  ])('links %s to the build, else the repository', (kind) => {
    expect(
      getNotificationLink({kind, metadata: {repository, build_id: 'abc-123'}}),
    ).toBe(`${repositoryPage}/build/abc-123`);
    expect(getNotificationLink({kind, metadata: {repository}})).toBe(
      repositoryPage,
    );
  });

  it.each(['quota_warning', 'quota_error'])(
    'links %s to the namespace settings, else nowhere',
    (kind) => {
      expect(getNotificationLink({kind, metadata: {namespace: 'myorg'}})).toBe(
        '/organization/myorg?tab=Settings',
      );
      expect(getNotificationLink({kind, metadata: {}})).toBeNull();
    },
  );

  it('links over_private_usage to the namespace', () => {
    expect(
      getNotificationLink({
        kind: 'over_private_usage',
        metadata: {namespace: 'myorg'},
      }),
    ).toBe('/organization/myorg');
  });

  it.each([
    ['maintenance', {from_date: 'a', to_date: 'b', reason: 'c'}],
    ['service_key_submitted', {kid: 'k', service: 's'}],
    ['assigned_authorization', {username: 'u'}],
    ['org_team_invite', {inviter: 'a', org: 'myorg', team: 't', code: 'x'}],
    ['password_required', {}],
    ['test_notification', {obj: 'x'}],
  ])('returns null for %s', (kind, metadata) => {
    expect(getNotificationLink({kind, metadata})).toBeNull();
  });

  it('returns null without metadata', () => {
    expect(getNotificationLink({kind: 'repo_push'})).toBeNull();
  });
});
