import React from 'react';
import {Control} from 'react-hook-form';
import {render, screen, userEvent} from 'src/test-utils';
import {Mirroring} from './Mirroring';
import {MirroringFormData} from './types';
import {getMirrorConfig} from 'src/resources/MirroringResource';

vi.mock('src/resources/MirroringResource', async (importOriginal) => ({
  ...(await importOriginal<typeof import('src/resources/MirroringResource')>()),
  getMirrorConfig: vi.fn(),
  createMirrorConfig: vi.fn(),
  updateMirrorConfig: vi.fn(),
}));

vi.mock('src/hooks/UseRepository', () => ({
  useRepository: () => ({
    repoDetails: {state: 'MIRROR'},
    errorLoadingRepoDetails: null,
    isLoading: false,
  }),
}));

vi.mock('src/hooks/useRobotAccounts', () => ({
  useFetchRobotAccounts: () => ({robots: []}),
}));

vi.mock('src/hooks/UseTeams', () => ({
  useFetchTeams: () => ({teams: []}),
}));

vi.mock('src/hooks/UseQuayConfig', () => ({
  useQuayConfig: () => ({config: {}}),
}));

// Plain inputs stand in for the real fields so a test can set any form value,
// including a blank start date the real date-time picker never emits.
vi.mock('./MirroringConfiguration', async () => {
  const {Controller} =
    await vi.importActual<typeof import('react-hook-form')>('react-hook-form');
  const fields = [
    'externalReference',
    'tags',
    'syncStartDate',
    'robotUsername',
  ] as const;
  return {
    MirroringConfiguration: ({
      control,
    }: {
      control: Control<MirroringFormData>;
    }) => (
      <>
        {fields.map((name) => (
          <Controller
            key={name}
            name={name}
            control={control}
            render={({field}) => (
              <input
                aria-label={name}
                value={field.value}
                onChange={field.onChange}
              />
            )}
          />
        ))}
      </>
    ),
  };
});

vi.mock('./MirroringHeader', () => ({MirroringHeader: () => null}));
vi.mock('./MirroringCredentials', () => ({MirroringCredentials: () => null}));
vi.mock('./MirroringAdvancedSettings', () => ({
  MirroringAdvancedSettings: () => null,
}));
vi.mock('./MirroringStatus', () => ({MirroringStatus: () => null}));
vi.mock('./MirroringModals', () => ({MirroringModals: () => null}));

const existingConfig = {
  is_enabled: true,
  external_reference: 'quay.io/library/alpine',
  external_registry_username: null,
  robot_username: 'testorg+bot',
  external_registry_config: {
    verify_tls: true,
    unsigned_images: false,
    proxy: {http_proxy: null, https_proxy: null, no_proxy: null},
  },
  sync_start_date: '2024-06-15T10:30:00Z',
  sync_interval: 86400,
  root_rule: {rule_kind: 'tag_glob_csv', rule_value: ['latest']},
  skopeo_timeout_interval: 300,
  architecture_filter: [],
  sync_status: 'NEVER_RUN',
};

function renderNewConfig() {
  vi.mocked(getMirrorConfig).mockRejectedValue({response: {status: 404}});
  render(<Mirroring namespace="testorg" repoName="testrepo" />);
}

async function fillRequiredFields() {
  await userEvent.type(
    screen.getByLabelText('externalReference'),
    'quay.io/library/alpine',
  );
  await userEvent.type(screen.getByLabelText('tags'), 'latest');
  await userEvent.type(screen.getByLabelText('robotUsername'), 'testorg+bot');
}

describe('Mirroring - start date', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('pre-fills the start date for a new config', async () => {
    renderNewConfig();
    const startDate = await screen.findByLabelText('syncStartDate');
    const value = (startDate as HTMLInputElement).value;
    expect(Math.abs(new Date(value).getTime() - Date.now())).toBeLessThan(
      120_000,
    );
  });

  it('enables Enable Mirror for a new config with the default date', async () => {
    renderNewConfig();
    await screen.findByLabelText('syncStartDate');
    await fillRequiredFields();
    expect(screen.getByTestId('submit-button')).toBeEnabled();
  });

  it('disables Enable Mirror for a new config without a start date', async () => {
    renderNewConfig();
    const startDate = await screen.findByLabelText('syncStartDate');
    await fillRequiredFields();
    await userEvent.clear(startDate);
    expect(screen.getByTestId('submit-button')).toBeDisabled();
  });

  it('disables Update Mirror for an existing config without a start date', async () => {
    vi.mocked(getMirrorConfig).mockResolvedValue(existingConfig as never);
    render(<Mirroring namespace="testorg" repoName="testrepo" />);
    const startDate = await screen.findByLabelText('syncStartDate');
    expect(startDate).not.toHaveValue('');
    await userEvent.clear(startDate);
    expect(screen.getByTestId('submit-button')).toHaveTextContent(
      'Update Mirror',
    );
    expect(screen.getByTestId('submit-button')).toBeDisabled();
  });
});
