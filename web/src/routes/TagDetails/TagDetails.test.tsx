import {render, screen, fireEvent} from '@testing-library/react';
import {within} from '@testing-library/dom';
import {RecoilRoot} from 'recoil';
import {useLocation, MemoryRouter, useSearchParams} from 'react-router-dom';
import {mocked} from 'ts-jest/utils';
import prettyBytes from 'pretty-bytes';
import TagDetails from './TagDetails';
import {
  Tag,
  TagsResponse,
  getTags,
  getSecurityDetails,
  getManifestByDigest,
  getLabels,
  SecurityDetailsResponse,
  VulnerabilitySeverity,
} from 'src/resources/TagResource';
import {formatDate} from 'src/libs/utils';

jest.mock('react-router-dom', () => ({
  ...(jest.requireActual('react-router-dom') as any),
  useLocation: jest.fn(),
  useNavigate: jest.fn(),
  useSearchParams: jest.fn(),
}));

jest.mock('src/resources/TagResource', () => ({
  ...(jest.requireActual('src/resources/TagResource') as any),
  getTags: jest.fn(),
  getManifestByDigest: jest.fn(),
  getSecurityDetails: jest.fn(),
  deleteTag: jest.fn(),
  getLabels: jest.fn(),
}));

const createTagResponse = (): TagsResponse => {
  return {
    page: 1,
    has_additional: false,
    tags: [],
  };
};
const createTag = (name = 'latest'): Tag => {
  return {
    name: name,
    is_manifest_list: false,
    last_modified: 'Thu, 02 Jun 2022 19:12:32 -0000',
    size: 100,
    manifest_digest: 'sha256:fd0922d',
    reversion: false,
    start_ts: 1654197152,
    manifest_list: null,
  };
};
const createLabelsResponse = () => {
  return {
    labels: [
      {
        id: '1',
        key: 'description',
        value: 'This is an example description label',
        source_type: 'manifest',
        media_type: 'text/plain',
      },
    ],
  };
};
const createSecurityResponse = (): SecurityDetailsResponse => {
  return {
    status: 'scanned',
    data: {
      Layer: {
        Name: 'sha256:a86508918ea51da557037edb30cef2a2768fe3982448a23b969a5066bf888940',
        ParentName: '',
        NamespaceName: '',
        IndexedByVersion: 4,
        Features: [
          {
            Name: 'rsync',
            VersionFormat: '',
            NamespaceName: '',
            AddedBy:
              'sha256:f606edb6a32a7c5bce00ab71be5f987ba16eb6bc68bd6c5cefe48bc8199552ca',
            Version: '3.1.3-12.el8',
            Vulnerabilities: [
              {
                Severity: VulnerabilitySeverity.High,
                NamespaceName: 'RHEL8-rhel-8.4-eus',
                Link: 'https://access.redhat.com/errata/RHSA-2022:2198 https://access.redhat.com/security/cve/CVE-2018-25032',
                FixedBy: '0:3.1.3-12.el8_4.1',
                Description:
                  'The rsync utility enables the users to copy and synchronize files locally or across a network. Synchronization with rsync is fast because rsync only sends the differences in files over the network instead of sending whole files. The rsync utility is also used as a mirroring tool.\n\nSecurity Fix(es):\n\n* zlib: A flaw found in zlib when compressing (not decompressing) certain inputs (CVE-2018-25032)\n\nFor more details about the security issue(s), including the impact, a CVSS score, acknowledgments, and other related information, refer to the CVE page(s) listed in the References section.',
                Name: 'RHSA-2022:2198: rsync security update (Important)',
                Metadata: {
                  UpdatedBy: 'RHEL8-rhel-8.4-eus',
                  RepoName: 'cpe:/a:redhat:rhel_eus:8.4::appstream',
                  RepoLink: null,
                  DistroName: 'Red Hat Enterprise Linux Server',
                  DistroVersion: '8',
                  NVD: {
                    CVSSv3: {
                      Vectors: 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H',
                      Score: 7.5,
                    },
                  },
                },
              },
              {
                Severity: VulnerabilitySeverity.High,
                NamespaceName: 'RHEL8-rhel-8.4-eus',
                Link: 'https://access.redhat.com/errata/RHSA-2022:2198 https://access.redhat.com/security/cve/CVE-2018-25032',
                FixedBy: '0:3.1.3-12.el8_4.1',
                Description:
                  'The rsync utility enables the users to copy and synchronize files locally or across a network. Synchronization with rsync is fast because rsync only sends the differences in files over the network instead of sending whole files. The rsync utility is also used as a mirroring tool.\n\nSecurity Fix(es):\n\n* zlib: A flaw found in zlib when compressing (not decompressing) certain inputs (CVE-2018-25032)\n\nFor more details about the security issue(s), including the impact, a CVSS score, acknowledgments, and other related information, refer to the CVE page(s) listed in the References section.',
                Name: 'RHSA-2022:2198: rsync security update (Important)',
                Metadata: {
                  UpdatedBy: 'RHEL8-rhel-8.4-eus',
                  RepoName: 'cpe:/o:redhat:rhel_eus:8.4::baseos',
                  RepoLink: null,
                  DistroName: 'Red Hat Enterprise Linux Server',
                  DistroVersion: '8',
                  NVD: {
                    CVSSv3: {
                      Vectors: 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H',
                      Score: 7.5,
                    },
                  },
                },
              },
            ],
          },
        ],
      },
    },
  };
};

type Test = {
  testId: string;
  name?: string;
  value: string;
};

const checkFieldValues = async (tests: Test[]) => {
  for (const test of tests) {
    const field = await screen.findByTestId(test.testId);
    expect(within(field).getByText(test.name)).toBeTruthy();
    expect(field).toHaveTextContent(test.value);
  }
};

const checkClipboardValues = async (tests: Test[]) => {
  for (const test of tests) {
    const clipboardCopy = (
      await screen.findByTestId(test.testId)
    ).querySelector('input');
    expect(clipboardCopy.value).toBe(test.value);
  }
};

test('Render simple tag', async () => {
  const mockResponse = createTagResponse();
  const mockTag = createTag();
  mockResponse.tags.push(mockTag);
  mocked(getTags, true).mockResolvedValue(mockResponse);
  mocked(getLabels, true).mockResolvedValue(createLabelsResponse());
  mocked(getSecurityDetails, true).mockResolvedValue(createSecurityResponse());
  mocked(useLocation, true).mockImplementation(() => ({
    ...jest.requireActual('react-router-dom').useLocation,
    pathname: '/organization/testorg/testrepo/latest',
  }));
  mocked(useSearchParams, true).mockImplementation(() => [
    new URLSearchParams(),
    jest.fn(),
  ]);
  render(
    <RecoilRoot>
      <TagDetails />
    </RecoilRoot>,
    {wrapper: MemoryRouter},
  );
  const tests: Test[] = [
    {
      testId: 'name',
      name: 'Name',
      value: mockTag.name,
    },
    {
      testId: 'creation',
      name: 'Creation',
      value: formatDate(mockTag.start_ts),
    },
    {
      testId: 'repository',
      name: 'Repository',
      value: 'testrepo',
    },
    {
      testId: 'modified',
      name: 'Modified',
      value: formatDate(mockTag.last_modified),
    },
    {
      testId: 'size',
      name: 'Size',
      value: prettyBytes(mockTag.size),
    },
    {
      testId: 'vulnerabilities',
      name: 'Vulnerabilities',
      value: '2 High',
    },
    {
      testId: 'labels',
      name: 'Labels',
      value: 'description = This is an example description label',
    },
  ];
  await checkFieldValues(tests);
  const clipboardCopyTests: Test[] = [
    {
      testId: 'podman-tag-clipboardcopy',
      value: 'podman pull quay.io/testorg/testrepo:latest',
    },
    {
      testId: 'docker-tag-clipboardcopy',
      value: 'docker pull quay.io/testorg/testrepo:latest',
    },
    {
      testId: 'podman-digest-clipboardcopy',
      value: 'podman pull quay.io/testorg/testrepo@' + mockTag.manifest_digest,
    },
    {
      testId: 'docker-digest-clipboardcopy',
      value: 'docker pull quay.io/testorg/testrepo@' + mockTag.manifest_digest,
    },
  ];
  expect(
    within(await screen.findByTestId('digest-clipboardcopy')).getByText(
      mockTag.manifest_digest,
    ),
  ).toBeTruthy();
  await checkClipboardValues(clipboardCopyTests);
});

test('Render manifest list tag', async () => {
  const mockResponse = createTagResponse();
  const mockTag = createTag();
  mockTag.is_manifest_list = true;
  mockResponse.tags.push(mockTag);

  const FIRST_MANIFEST = 0,
    SECOND_MANIFEST = 1;
  const mockManifest = {
    schemaVersion: 2,
    mediaType: 'application/vnd.oci.image.index.v1+json',
    manifests: [
      {
        digest: 'sha256:abcdefghijk',
        size: 1,
        platform: {
          architecture: 'ppc64le',
          os: 'linux',
        },
      },
      {
        digest: 'sha256:12345678910',
        size: 2,
        platform: {
          architecture: 'amd64',
          os: 'linux',
        },
      },
    ],
  };

  mocked(getTags, true).mockResolvedValue(mockResponse);
  mocked(getLabels, true).mockResolvedValue(createLabelsResponse());
  mocked(getSecurityDetails, true).mockResolvedValue(createSecurityResponse());
  mocked(getManifestByDigest, true).mockResolvedValue({
    digest: mockTag.manifest_digest,
    is_manifest_list: true,
    manifest_data: JSON.stringify(mockManifest),
  });
  mocked(useLocation, true).mockImplementation(() => ({
    ...jest.requireActual('react-router-dom').useLocation,
    pathname: '/organization/testorg/testrepo/latest',
  }));
  mocked(useSearchParams, true).mockImplementation(() => [
    new URLSearchParams(),
    jest.fn(),
  ]);

  render(
    <RecoilRoot>
      <TagDetails />
    </RecoilRoot>,
    {wrapper: MemoryRouter},
  );

  const archSelect = await screen.findByText('ppc64le');
  expect(archSelect).toBeTruthy();

  const tests: Test[] = [
    {
      testId: 'name',
      name: 'Name',
      value: mockTag.name,
    },
    {
      testId: 'creation',
      name: 'Creation',
      value: formatDate(mockTag.start_ts),
    },
    {
      testId: 'repository',
      name: 'Repository',
      value: 'testrepo',
    },
    {
      testId: 'modified',
      name: 'Modified',
      value: formatDate(mockTag.last_modified),
    },
    {
      testId: 'size',
      name: 'Size',
      value: prettyBytes(mockManifest.manifests[FIRST_MANIFEST].size),
    },
    {
      testId: 'vulnerabilities',
      name: 'Vulnerabilities',
      value: '2 High',
    },
    {
      testId: 'labels',
      name: 'Labels',
      value: 'description = This is an example description label',
    },
  ];
  await checkFieldValues(tests);

  let clipboardCopyTests: Test[] = [
    {
      testId: 'podman-tag-clipboardcopy',
      value: 'podman pull quay.io/testorg/testrepo:latest',
    },
    {
      testId: 'docker-tag-clipboardcopy',
      value: 'docker pull quay.io/testorg/testrepo:latest',
    },
    {
      testId: 'podman-digest-clipboardcopy',
      value:
        'podman pull quay.io/testorg/testrepo@' +
        mockManifest.manifests[FIRST_MANIFEST].digest,
    },
    {
      testId: 'docker-digest-clipboardcopy',
      value:
        'docker pull quay.io/testorg/testrepo@' +
        mockManifest.manifests[FIRST_MANIFEST].digest,
    },
  ];
  expect(
    within(await screen.findByTestId('digest-clipboardcopy')).getByText(
      mockManifest.manifests[FIRST_MANIFEST].digest,
    ),
  ).toBeTruthy();
  await checkClipboardValues(clipboardCopyTests);

  // Select the other architecture
  fireEvent(
    archSelect,
    new MouseEvent('click', {bubbles: true, cancelable: true}),
  );
  expect(await screen.findAllByText('ppc64le')).toBeTruthy();
  const secondArchOption = await screen.findByText('amd64');
  expect(secondArchOption).toBeTruthy();
  fireEvent(
    secondArchOption,
    new MouseEvent('click', {bubbles: true, cancelable: true}),
  );

  tests[4].value = prettyBytes(mockManifest.manifests[SECOND_MANIFEST].size);
  await checkFieldValues(tests);

  clipboardCopyTests = [
    {
      testId: 'podman-tag-clipboardcopy',
      value: 'podman pull quay.io/testorg/testrepo:latest',
    },
    {
      testId: 'docker-tag-clipboardcopy',
      value: 'docker pull quay.io/testorg/testrepo:latest',
    },
    {
      testId: 'podman-digest-clipboardcopy',
      value:
        'podman pull quay.io/testorg/testrepo@' +
        mockManifest.manifests[SECOND_MANIFEST].digest,
    },
    {
      testId: 'docker-digest-clipboardcopy',
      value:
        'docker pull quay.io/testorg/testrepo@' +
        mockManifest.manifests[SECOND_MANIFEST].digest,
    },
  ];
  expect(
    within(await screen.findByTestId('digest-clipboardcopy')).getByText(
      mockManifest.manifests[SECOND_MANIFEST].digest,
    ),
  ).toBeTruthy();
  await checkClipboardValues(clipboardCopyTests);
});
