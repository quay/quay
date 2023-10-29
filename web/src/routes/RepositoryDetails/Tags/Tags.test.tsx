import Tags from './Tags';
import {render, screen, fireEvent} from '@testing-library/react';
import {RecoilRoot} from 'recoil';
import {mocked} from 'ts-jest/utils';
import {
  Tag,
  TagsResponse,
  getTags,
  deleteTag,
  getSecurityDetails,
  SecurityDetailsResponse,
  VulnerabilitySeverity,
} from 'src/resources/TagResource';
import {MemoryRouter} from 'react-router-dom';

jest.mock('src/resources/TagResource', () => ({
  ...(jest.requireActual('src/resources/TagResource') as any),
  getTags: jest.fn(),
  getManifestByDigest: jest.fn(),
  getSecurityDetails: jest.fn(),
  deleteTag: jest.fn(),
}));

const testOrg = 'testorg';
const testRepo = 'testrepo';
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
const createSecurityDetailsResponse = (): SecurityDetailsResponse => {
  return {
    status: 'scanned',
    data: {
      Layer: {
        Name: 'sha256:a86508918ea51da557037edb30cef2a2768fe3982448a23b969a5066bf888940',
        ParentName: '',
        NamespaceName: '',
        IndexedByVersion: 1,
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

test('Tags should render', async () => {
  mocked(getTags, true).mockResolvedValue(createTagResponse());
  mocked(getSecurityDetails, true).mockResolvedValue(
    createSecurityDetailsResponse(),
  );
  render(
    <RecoilRoot>
      <Tags organization={testOrg} repository={testRepo} />
    </RecoilRoot>,
    {wrapper: MemoryRouter},
  );
  const message = await screen.findByText('This repository is empty.');
  expect(message).toBeTruthy();
});

test('Tags should appear in list', async () => {
  const mockResponse = createTagResponse();
  mockResponse.tags.push(createTag());
  mocked(getTags, true).mockResolvedValue(mockResponse);
  mocked(getSecurityDetails, true).mockResolvedValue(
    createSecurityDetailsResponse(),
  );
  render(
    <RecoilRoot>
      <Tags organization={testOrg} repository={testRepo} />
    </RecoilRoot>,
    {wrapper: MemoryRouter},
  );
  const message = await screen.findByText('latest');
  expect(message).toBeTruthy();
});

test('Filter search should return matching list', async () => {
  const tagNames = ['latest', 'slim', 'alpine'];
  const mockResponse = createTagResponse();
  for (const tag of tagNames) {
    mockResponse.tags.push(createTag(tag));
  }
  mocked(getTags, true).mockResolvedValue(mockResponse);
  mocked(getSecurityDetails, true).mockResolvedValue(
    createSecurityDetailsResponse(),
  );
  render(
    <RecoilRoot>
      <Tags organization={testOrg} repository={testRepo} />
    </RecoilRoot>,
    {wrapper: MemoryRouter},
  );
  expect(await screen.findByText('latest')).toBeTruthy();
  expect(await screen.findByText('slim')).toBeTruthy();
  expect(await screen.findByText('alpine')).toBeTruthy();
  const filterTextBox = screen.getByPlaceholderText('Filter by Tag name');
  fireEvent.change(filterTextBox, {target: {value: 'latest'}});
  expect(await screen.findByText('latest')).toBeTruthy();
  expect(screen.queryByText('slim')).toBeNull();
  expect(screen.queryByText('alpine')).toBeNull();
});

test('Updating per page should update table content', async () => {
  const mockResponse: TagsResponse = createTagResponse();
  for (let i = 0; i < 40; i++) {
    mockResponse.tags.push(createTag(`tag${i}`));
  }
  mocked(getTags, true).mockResolvedValue(mockResponse);
  mocked(getSecurityDetails, true).mockResolvedValue(
    createSecurityDetailsResponse(),
  );
  const {container} = render(
    <RecoilRoot>
      <Tags organization={testOrg} repository={testRepo} />
    </RecoilRoot>,
    {wrapper: MemoryRouter},
  );
  const initialRows = await screen.findAllByTestId('table-entry');
  expect(initialRows.length).toBe(25);
  const perPageButton = (await screen.findByTestId('pagination')).querySelector(
    'button',
  ); // Assumes 1st button is per page
  fireEvent(
    perPageButton,
    new MouseEvent('click', {bubbles: true, cancelable: true}),
  );
  fireEvent(
    await screen.findByText('10 per page'),
    new MouseEvent('click', {bubbles: true, cancelable: true}),
  );
  const updatedRows = screen.getAllByTestId('table-entry');
  expect(updatedRows.length).toBe(10);
});

test('Updating page should update table content', async () => {
  const mockResponse: TagsResponse = createTagResponse();
  for (let i = 0; i < 40; i++) {
    mockResponse.tags.push(createTag(`tag${i}`));
  }
  mocked(getTags, true).mockResolvedValue(mockResponse);
  mocked(getSecurityDetails, true).mockResolvedValue(
    createSecurityDetailsResponse(),
  );
  const {container} = render(
    <RecoilRoot>
      <Tags organization={testOrg} repository={testRepo} />
    </RecoilRoot>,
    {wrapper: MemoryRouter},
  );
  const initialRows = await screen.findAllByTestId('table-entry');
  expect(initialRows.length).toBe(25);
  fireEvent(
    screen.getByLabelText('Go to next page'),
    new MouseEvent('click', {bubbles: true, cancelable: true}),
  );
  const updatedRows = screen.getAllByTestId('table-entry');
  expect(updatedRows.length).toBe(15);
});

test('Copy modal should show org and repo', async () => {
  const mockResponse = createTagResponse();
  const tag = createTag();
  mockResponse.tags.push(tag);
  mocked(getTags, true).mockResolvedValue(mockResponse);
  mocked(getSecurityDetails, true).mockResolvedValue(
    createSecurityDetailsResponse(),
  );
  render(
    <RecoilRoot>
      <Tags organization={testOrg} repository={testRepo} />
    </RecoilRoot>,
    {wrapper: MemoryRouter},
  );
  expect(await screen.findByText(tag.name)).toBeTruthy();
  fireEvent.mouseOver(screen.getByTestId('pull'));
  expect(
    (await screen.findByTestId(`copy-tag-podman`)).querySelector('input').value,
  ).toBe(`podman pull quay.io/${testOrg}/${testRepo}:${tag.name}`);
  expect(
    screen.getByTestId(`copy-digest-podman`).querySelector('input').value,
  ).toBe(`podman pull quay.io/${testOrg}/${testRepo}@${tag.manifest_digest}`);
  expect(
    screen.getByTestId(`copy-tag-docker`).querySelector('input').value,
  ).toBe(`docker pull quay.io/${testOrg}/${testRepo}:${tag.name}`);
  expect(
    screen.getByTestId(`copy-digest-docker`).querySelector('input').value,
  ).toBe(`docker pull quay.io/${testOrg}/${testRepo}@${tag.manifest_digest}`);
});

test('Delete a single tag', async () => {
  const mockResponse = createTagResponse();
  const tag = createTag();
  mockResponse.tags.push(tag);
  mocked(getTags, true)
    .mockResolvedValueOnce(mockResponse)
    .mockResolvedValueOnce(createTagResponse());
  mocked(deleteTag, true).mockResolvedValue();
  mocked(getSecurityDetails, true).mockResolvedValue(
    createSecurityDetailsResponse(),
  );
  render(
    <RecoilRoot>
      <Tags organization={testOrg} repository={testRepo} />
    </RecoilRoot>,
    {wrapper: MemoryRouter},
  );
  expect(await screen.findByText(tag.name)).toBeTruthy();
  const rowSelect = screen.getByLabelText('Select row 0', {selector: 'input'});
  fireEvent(
    rowSelect,
    new MouseEvent('click', {bubbles: true, cancelable: true}),
  );
  const actionsKebab = screen.getByLabelText('Actions', {selector: 'button'});
  fireEvent(
    actionsKebab,
    new MouseEvent('click', {bubbles: true, cancelable: true}),
  );
  fireEvent(
    screen.getByText('Delete'),
    new MouseEvent('click', {bubbles: true, cancelable: true}),
  );
  expect(screen.getByText('Delete the following tag?')).toBeTruthy();
  expect(screen.getByTestId('delete-tags-modal')).toHaveTextContent('latest');
  expect(screen.getByText('Cancel')).toBeTruthy();
  expect(screen.getByText('Delete')).toBeTruthy();
  fireEvent(
    screen.getByText('Delete'),
    new MouseEvent('click', {bubbles: true, cancelable: true}),
  );
  expect(await screen.findByText('This repository is empty.')).toBeTruthy();
});

test('Delete a multiple tags', async () => {
  const tagNames = ['latest', 'slim', 'alpine'];
  const mockResponse = createTagResponse();
  for (const tag of tagNames) {
    mockResponse.tags.push(createTag(tag));
  }
  mocked(getTags, true)
    .mockResolvedValueOnce(mockResponse)
    .mockResolvedValueOnce(createTagResponse());
  mocked(deleteTag, true).mockResolvedValue();
  mocked(getSecurityDetails, true).mockResolvedValue(
    createSecurityDetailsResponse(),
  );
  render(
    <RecoilRoot>
      <Tags organization={testOrg} repository={testRepo} />
    </RecoilRoot>,
    {wrapper: MemoryRouter},
  );
  expect(await screen.findByText('latest')).toBeTruthy();
  expect(await screen.findByText('slim')).toBeTruthy();
  expect(await screen.findByText('alpine')).toBeTruthy();
  const rowSelect = screen.getByLabelText('Select all rows', {
    selector: 'input',
  });
  fireEvent(
    rowSelect,
    new MouseEvent('click', {bubbles: true, cancelable: true}),
  );
  const actionsKebab = screen.getByLabelText('Actions', {selector: 'button'});
  fireEvent(
    actionsKebab,
    new MouseEvent('click', {bubbles: true, cancelable: true}),
  );
  fireEvent(
    screen.getByText('Delete'),
    new MouseEvent('click', {bubbles: true, cancelable: true}),
  );
  expect(screen.getByText('Delete the following tags?')).toBeTruthy();
  expect(screen.getByTestId('delete-tags-modal')).toHaveTextContent('latest');
  expect(screen.getByTestId('delete-tags-modal')).toHaveTextContent('slim');
  expect(screen.getByTestId('delete-tags-modal')).toHaveTextContent('alpine');
  expect(
    screen.getByText('This operation can take several minutes.'),
  ).toBeTruthy();
  expect(screen.getByText('Cancel')).toBeTruthy();
  expect(screen.getByText('Delete')).toBeTruthy();
  const deletebutton = screen.getByText('Delete');
  fireEvent(
    deletebutton,
    new MouseEvent('click', {bubbles: true, cancelable: true}),
  );
  expect(await screen.findByText('This repository is empty.')).toBeTruthy();
});
