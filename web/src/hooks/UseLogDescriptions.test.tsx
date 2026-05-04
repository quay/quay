import {renderHook} from '@testing-library/react';
import {render} from '@testing-library/react';
import {useLogDescriptions} from './UseLogDescriptions';
import React from 'react';

vi.mock('./UseEvents', () => ({
  useEvents: vi.fn(() => ({
    events: [
      {type: 'repo_push', title: 'Push to Repository'},
      {type: 'vulnerability_found', title: 'Package Vulnerability Found'},
      {type: 'build_failure', title: 'Image build failed'},
    ],
  })),
}));

vi.mock('src/libs/utils', () => ({
  isNullOrUndefined: vi.fn((v) => v === null || v === undefined),
  humanizeTimeForExpiry: vi.fn((s: number) => `${s}s`),
  formatDate: vi.fn((ts: string | number) => `formatted-${ts}`),
}));

function getDescriptions() {
  const {result} = renderHook(() => useLogDescriptions());
  return result.current;
}

function renderDescription(node: React.ReactNode): string {
  const {container} = render(React.createElement(React.Fragment, null, node));
  return container.textContent || '';
}

describe('UseLogDescriptions', () => {
  describe('user events', () => {
    it('user_create with superuser', () => {
      const desc = getDescriptions();
      const text = renderDescription(
        desc.user_create({superuser: 'admin', username: 'newuser'}),
      );
      expect(text).toContain('admin');
      expect(text).toContain('newuser');
    });

    it('user_create without superuser', () => {
      const desc = getDescriptions();
      const text = renderDescription(desc.user_create({username: 'newuser'}));
      expect(text).toContain('newuser');
      expect(text).not.toContain('Superuser');
    });

    it('user_delete with superuser', () => {
      const desc = getDescriptions();
      const text = renderDescription(
        desc.user_delete({superuser: 'admin', username: 'olduser'}),
      );
      expect(text).toContain('admin');
      expect(text).toContain('olduser');
    });

    it('user_change_password', () => {
      const desc = getDescriptions();
      expect(desc.user_change_password({username: 'alice'})).toContain('alice');
    });

    it('user_change_email with superuser', () => {
      const desc = getDescriptions();
      expect(
        desc.user_change_email({
          superuser: 'admin',
          old_email: 'old@ex.com',
          email: 'new@ex.com',
        }),
      ).toContain('admin');
    });

    it('user_change_invoicing enable', () => {
      const desc = getDescriptions();
      expect(desc.user_change_invoicing({invoice_email: true})).toBe(
        'Enabled email invoicing',
      );
    });

    it('user_change_invoicing set address', () => {
      const desc = getDescriptions();
      expect(
        desc.user_change_invoicing({invoice_email_address: 'test@ex.com'}),
      ).toContain('test@ex.com');
    });

    it('user_change_invoicing disable', () => {
      const desc = getDescriptions();
      expect(desc.user_change_invoicing({})).toBe('Disabled email invoicing');
    });
  });

  describe('repository events', () => {
    it('push_repo with tag', () => {
      const desc = getDescriptions();
      const text = renderDescription(
        desc.push_repo({tag: 'v1.0', namespace: 'myorg', repo: 'myrepo'}),
      );
      expect(text).toContain('v1.0');
      expect(text).toContain('myorg/myrepo');
    });

    it('push_repo without tag or release', () => {
      const desc = getDescriptions();
      const text = renderDescription(
        desc.push_repo({namespace: 'myorg', repo: 'myrepo'}),
      );
      expect(text).toContain('Repository push');
    });

    it('delete_repo', () => {
      const desc = getDescriptions();
      const text = renderDescription(desc.delete_repo({repo: 'myrepo'}));
      expect(text).toContain('myrepo');
    });

    it('create_repo', () => {
      const desc = getDescriptions();
      const text = renderDescription(
        desc.create_repo({namespace: 'myorg', repo: 'myrepo'}),
      );
      expect(text).toContain('myorg/myrepo');
    });

    it('change_repo_visibility', () => {
      const desc = getDescriptions();
      expect(
        desc.change_repo_visibility({
          namespace: 'myorg',
          repo: 'myrepo',
          visibility: 'public',
        }),
      ).toContain('public');
    });
  });

  describe('tag events', () => {
    it('delete_tag', () => {
      const desc = getDescriptions();
      const text = renderDescription(
        desc.delete_tag({
          tag: 'latest',
          namespace: 'myorg',
          repo: 'myrepo',
          username: 'alice',
        }),
      );
      expect(text).toContain('latest');
      expect(text).toContain('alice');
    });

    it('revert_tag with manifest_digest', () => {
      const desc = getDescriptions();
      expect(
        desc.revert_tag({tag: 'v1', manifest_digest: 'sha256:abc'}),
      ).toContain('sha256:abc');
    });

    it('revert_tag with image fallback', () => {
      const desc = getDescriptions();
      expect(desc.revert_tag({tag: 'v1', image: 'img123'})).toContain('img123');
    });

    it('change_tag_expiration with both dates', () => {
      const desc = getDescriptions();
      const text = desc.change_tag_expiration({
        tag: 'latest',
        expiration_date: '1709251200',
        old_expiration_date: '1706659200',
      });
      expect(text).toContain('latest');
      expect(text).toContain('formatted-');
    });

    it('change_tag_expiration with no dates', () => {
      const desc = getDescriptions();
      expect(desc.change_tag_expiration({tag: 'latest'})).toContain(
        'no longer expire',
      );
    });
  });

  describe('organization events', () => {
    it('org_create', () => {
      const desc = getDescriptions();
      const text = renderDescription(desc.org_create({namespace: 'myorg'}));
      expect(text).toContain('myorg');
    });

    it('org_create_team', () => {
      const desc = getDescriptions();
      const text = renderDescription(desc.org_create_team({team: 'devs'}));
      expect(text).toContain('devs');
    });

    it('org_add_team_member', () => {
      const desc = getDescriptions();
      const text = renderDescription(
        desc.org_add_team_member({member: 'alice', team: 'devs'}),
      );
      expect(text).toContain('alice');
      expect(text).toContain('devs');
    });

    it('org_invite_team_member with user', () => {
      const desc = getDescriptions();
      const text = renderDescription(
        desc.org_invite_team_member({user: 'alice', team: 'devs'}),
      );
      expect(text).toContain('alice');
    });

    it('org_invite_team_member with email', () => {
      const desc = getDescriptions();
      const text = renderDescription(
        desc.org_invite_team_member({email: 'alice@ex.com', team: 'devs'}),
      );
      expect(text).toContain('alice@ex.com');
    });
  });

  describe('mirror events', () => {
    it('repo_mirror_config_changed with sync_status SYNC_CANCEL', () => {
      const desc = getDescriptions();
      expect(
        desc.repo_mirror_config_changed({
          changed: 'sync_status',
          to: 'SYNC_CANCEL',
        }),
      ).toBe('Mirror canceled');
    });

    it('repo_mirror_config_changed with sync_status SYNC_NOW', () => {
      const desc = getDescriptions();
      expect(
        desc.repo_mirror_config_changed({
          changed: 'sync_status',
          to: 'SYNC_NOW',
        }),
      ).toBe('Immediate mirror scheduled');
    });

    it('repo_mirror_config_changed with external_registry', () => {
      const desc = getDescriptions();
      expect(
        desc.repo_mirror_config_changed({
          changed: 'external_registry',
          to: 'docker.io',
        }),
      ).toContain('External Registry');
    });
  });

  describe('permission events', () => {
    it('change_repo_permission for user', () => {
      const desc = getDescriptions();
      const text = renderDescription(
        desc.change_repo_permission({
          username: 'alice',
          repo: 'myrepo',
          role: 'admin',
        }),
      );
      expect(text).toContain('alice');
      expect(text).toContain('admin');
    });

    it('change_repo_permission for team', () => {
      const desc = getDescriptions();
      const text = renderDescription(
        desc.change_repo_permission({
          team: 'devs',
          repo: 'myrepo',
          role: 'write',
        }),
      );
      expect(text).toContain('devs');
    });
  });

  describe('notification events', () => {
    it('add_repo_notification', () => {
      const desc = getDescriptions();
      expect(
        desc.add_repo_notification({
          event: 'repo_push',
          namespace: 'myorg',
          repo: 'myrepo',
        }),
      ).toContain('Push to Repository');
    });
  });

  describe('build events', () => {
    it('build_dockerfile without trigger', () => {
      const desc = getDescriptions();
      expect(
        desc.build_dockerfile({namespace: 'myorg', repo: 'myrepo'}),
      ).toContain('Build from Dockerfile');
    });

    it('build_dockerfile with github trigger', () => {
      const desc = getDescriptions();
      expect(
        desc.build_dockerfile({
          namespace: 'myorg',
          repo: 'myrepo',
          trigger_id: 't1',
          service: 'github',
          config: JSON.stringify({build_source: 'myorg/myrepo'}),
        }),
      ).toContain('push to GitHub');
    });
  });

  describe('service key events', () => {
    it('service_key_create preshared', () => {
      const desc = getDescriptions();
      const text = renderDescription(
        desc.service_key_create({
          preshared: true,
          name: 'mykey',
          service: 'clair',
        }),
      );
      expect(text).toContain('preshared');
      expect(text).toContain('mykey');
    });

    it('service_key_create non-preshared with kid fallback', () => {
      const desc = getDescriptions();
      const text = renderDescription(
        desc.service_key_create({
          kid: 'abcdef123456789',
          service: 'clair',
          user_agent: 'scanner/1.0',
        }),
      );
      expect(text).toContain('abcdef123456');
    });
  });

  describe('autoprune events', () => {
    it('create_namespace_autoprune_policy', () => {
      const desc = getDescriptions();
      expect(
        desc.create_namespace_autoprune_policy({
          method: 'number_of_tags',
          value: '10',
          namespace: 'myorg',
        }),
      ).toContain('number_of_tags:10');
    });

    it('create_namespace_autoprune_policy with tag_pattern', () => {
      const desc = getDescriptions();
      expect(
        desc.create_namespace_autoprune_policy({
          method: 'number_of_tags',
          value: '10',
          namespace: 'myorg',
          tag_pattern: 'v*',
          tag_pattern_matches: 'true',
        }),
      ).toContain('tagPattern:v*');
    });
  });

  describe('immutability events', () => {
    it('create_immutability_policy for repository', () => {
      const desc = getDescriptions();
      const text = renderDescription(
        desc.create_immutability_policy({
          namespace: 'myorg',
          repo: 'myrepo',
          tag_pattern: 'v*',
          tag_pattern_matches: 'true',
        }),
      );
      expect(text).toContain('matching');
      expect(text).toContain('v*');
      expect(text).toContain('myorg/myrepo');
    });

    it('create_immutability_policy for namespace (NOT matching)', () => {
      const desc = getDescriptions();
      const text = renderDescription(
        desc.create_immutability_policy({
          namespace: 'myorg',
          tag_pattern: 'dev-*',
          tag_pattern_matches: 'false',
        }),
      );
      expect(text).toContain('NOT matching');
    });
  });

  describe('login events', () => {
    it('login_success v2auth with robot', () => {
      const desc = getDescriptions();
      const text = renderDescription(
        desc.login_success({type: 'v2auth', kind: 'robot', robot: 'myorg+bot'}),
      );
      expect(text).toContain('myorg+bot');
    });

    it('login_success non-v2auth', () => {
      const desc = getDescriptions();
      expect(desc.login_success({type: 'quayauth'})).toBe('Login to Quay');
    });

    it('login_failure v2auth with robot', () => {
      const desc = getDescriptions();
      expect(
        desc.login_failure({
          type: 'v2auth',
          kind: 'robot',
          robot: 'myorg+bot',
        }),
      ).toContain('robot myorg+bot');
    });
  });

  describe('quota events', () => {
    it('org_create_quota', () => {
      const desc = getDescriptions();
      const text = renderDescription(
        desc.org_create_quota({limit: '10 GB', namespace: 'myorg'}),
      );
      expect(text).toContain('10 GB');
      expect(text).toContain('myorg');
    });
  });
});
