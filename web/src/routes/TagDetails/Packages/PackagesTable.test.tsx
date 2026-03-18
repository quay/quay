import {render, screen} from '@testing-library/react';
import PackagesTable from './PackagesTable';
import {Feature, Layer, VulnerabilitySeverity} from 'src/resources/TagResource';

const layers: Layer[] = [
  {
    index: 0,
    compressed_size: 123,
    is_remote: false,
    urls: [],
    command: ['/bin/sh', '-c', 'yum install shadow-utils'],
    comment: '',
    author: '',
    blob_digest: 'sha256:layer1',
    created_datetime: '2026-01-01T00:00:00Z',
  },
];

const features: Feature[] = [
  {
    Name: 'shadow-utils',
    VersionFormat: 'rpm',
    NamespaceName: 'rhel',
    AddedBy: 'sha256:layer1.something',
    Version: '4.6',
    Vulnerabilities: [
      {
        Severity: VulnerabilitySeverity.High,
        NamespaceName: 'rhel',
        Link: 'https://example.com/CVE-1',
        FixedBy: '',
        Description: 'example vulnerability',
        Name: 'CVE-1',
        Metadata: {
          UpdatedBy: '',
          RepoName: '',
          RepoLink: '',
          DistroName: '',
          DistroVersion: '',
          NVD: {
            CVSSv3: {
              Vectors: '',
              Score: 0,
            },
          },
        },
      },
    ],
  },
  {
    Name: 'coreutils',
    VersionFormat: 'rpm',
    NamespaceName: 'rhel',
    AddedBy: 'sha256:missing.something',
    Version: '9.0',
    Vulnerabilities: [],
  },
];

describe('PackagesTable', () => {
  it('renders Introduced In Layer values from matching manifest layers', () => {
    render(<PackagesTable features={features} layers={layers} />);

    expect(screen.getByText('Introduced In Layer')).toBeInTheDocument();
    expect(
      screen.getByText('/bin/sh -c yum install shadow-utils'),
    ).toBeInTheDocument();
    expect(screen.getByText('(No Command)')).toBeInTheDocument();
  });
});
