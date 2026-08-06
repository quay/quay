import {render, screen} from 'src/test-utils';
import {OrgMirroringStatus} from './OrgMirroringStatus';
import {OrgMirrorConfig} from 'src/resources/OrgMirrorResource';

describe('OrgMirroringStatus', () => {
  const baseConfig = {
    id: 1,
    is_enabled: true,
    external_registry: 'quay.io',
    external_namespace: 'test',
    sync_interval: 3600,
    sync_start_date: '2026-01-01T00:00:00Z',
    sync_expiration_date: null,
    robot_username: 'org+robot',
    root_rule: {rule_kind: 'tag_glob_csv', rule_value: ['*']},
    external_registry_config: {},
    repo_sync_status_counts: {SYNCING: 1, SYNC_NOW: 0, SUCCESS: 5},
  };

  it('disables cancel sync button when onCancelSync is undefined', () => {
    render(
      <OrgMirroringStatus
        config={baseConfig as unknown as OrgMirrorConfig}
        isVerifying={false}
        isCancellingSync={false}
        onCancelSync={undefined}
        onVerifyConnection={vi.fn()}
      />,
    );
    const cancelBtn = screen.getByTestId('cancel-sync-button');
    expect(cancelBtn).toBeDisabled();
  });

  it('disables verify connection button when onVerifyConnection is undefined', () => {
    render(
      <OrgMirroringStatus
        config={baseConfig as unknown as OrgMirrorConfig}
        isVerifying={false}
        isCancellingSync={false}
        onCancelSync={vi.fn()}
        onVerifyConnection={undefined}
      />,
    );
    const verifyBtn = screen.getByTestId('verify-connection-button');
    expect(verifyBtn).toBeDisabled();
  });

  it('enables buttons when callbacks are provided', () => {
    render(
      <OrgMirroringStatus
        config={baseConfig as unknown as OrgMirrorConfig}
        isVerifying={false}
        isCancellingSync={false}
        onCancelSync={vi.fn()}
        onVerifyConnection={vi.fn()}
      />,
    );
    const cancelBtn = screen.getByTestId('cancel-sync-button');
    const verifyBtn = screen.getByTestId('verify-connection-button');
    expect(cancelBtn).not.toBeDisabled();
    expect(verifyBtn).not.toBeDisabled();
  });

  it('returns null when config is null', () => {
    const {container} = render(
      <OrgMirroringStatus
        config={null}
        isVerifying={false}
        isCancellingSync={false}
        onCancelSync={vi.fn()}
        onVerifyConnection={vi.fn()}
      />,
    );
    expect(container.firstChild).toBeNull();
  });
});
