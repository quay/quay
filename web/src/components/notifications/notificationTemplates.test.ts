import {getNotificationLink} from './notificationTemplates';

describe('getNotificationLink', () => {
  const repository = 'myorg/myrepo';

  it.each([
    'repo_push',
    'repo_mirror_sync_started',
    'repo_mirror_sync_success',
    'repo_mirror_sync_failed',
    'repo_image_expiry',
  ])('links %s to the repository', (kind) => {
    expect(getNotificationLink({kind, metadata: {repository}})).toBe(
      '/repository/myorg/myrepo',
    );
  });

  it('links vulnerability_found to the repository tags tab', () => {
    expect(
      getNotificationLink({
        kind: 'vulnerability_found',
        metadata: {repository, vulnerability: {priority: 'High'}},
      }),
    ).toBe('/repository/myorg/myrepo?tab=tags');
  });

  it.each([
    'build_queued',
    'build_start',
    'build_success',
    'build_failure',
    'build_cancelled',
  ])('links %s to the build', (kind) => {
    expect(
      getNotificationLink({kind, metadata: {repository, build_id: 'abc-123'}}),
    ).toBe('/repository/myorg/myrepo/build/abc-123');
  });

  it('links a build without a build_id to the repository', () => {
    expect(
      getNotificationLink({kind: 'build_failure', metadata: {repository}}),
    ).toBe('/repository/myorg/myrepo');
  });

  it.each(['quota_warning', 'quota_error'])(
    'links %s to the namespace',
    (kind) => {
      expect(getNotificationLink({kind, metadata: {namespace: 'myorg'}})).toBe(
        '/organization/myorg',
      );
    },
  );

  it('returns null for a kind without a page', () => {
    expect(
      getNotificationLink({kind: 'password_required', metadata: {repository}}),
    ).toBeNull();
  });

  it('returns null without metadata', () => {
    expect(getNotificationLink({kind: 'repo_push'})).toBeNull();
  });
});
