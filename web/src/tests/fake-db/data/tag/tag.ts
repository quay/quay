import {mock} from 'src/tests/fake-db/MockAxios';
import {AxiosRequestConfig} from 'axios';
import {TagsResponse, Tag} from 'src/resources/TagResource';

let tags: Tag[] = [
  {
    name: 'latest',
    is_manifest_list: false,
    last_modified: 'Thu, 02 Jun 2022 19:12:32 -0000',
    size: 100,
    manifest_digest:
      'sha256:1234567890101112150f0d3de5f80a38f65a85e709b77fd24491253990f306be',
    reversion: false,
    start_ts: 1654197152,
    manifest_list: undefined,
  },
  {
    name: 'manifestlist',
    is_manifest_list: true,
    last_modified: 'Thu, 02 Jun 2022 19:12:32 -0000',
    size: 100,
    manifest_digest:
      'sha256:abcdefghij3759fb50f0d3de5f80a38f65a85e709b77fd24491253990f30b6be',
    reversion: false,
    start_ts: 1654197152,
    manifest_list: {
      schemaVersion: 2,
      mediaType: '',
      manifests: [],
    },
  },
  {
    name: 'securityreportqueued',
    is_manifest_list: false,
    last_modified: 'Thu, 02 Jun 2022 19:12:32 -0000',
    size: 100,
    manifest_digest:
      'sha256:securityreportqueuedd3de5f80a38f65a85e709b77fd24491253990f30b6be',
    reversion: false,
    start_ts: 1654197152,
    manifest_list: undefined,
  },
  {
    name: 'securityreportfailed',
    is_manifest_list: false,
    last_modified: 'Thu, 02 Jun 2022 19:12:32 -0000',
    size: 100,
    manifest_digest:
      'sha256:securityreportfailedd3de5f80a38f65a85e709b77fd24491253990f30b6be',
    reversion: false,
    start_ts: 1654197152,
    manifest_list: undefined,
  },
  {
    name: 'securityreportunsupported',
    is_manifest_list: false,
    last_modified: 'Thu, 02 Jun 2022 19:12:32 -0000',
    size: 100,
    manifest_digest:
      'sha256:securityreportunsupported80a38f65a85e709b77dfd24491253990f30b6be',
    reversion: false,
    start_ts: 1654197152,
    manifest_list: undefined,
  },
  {
    name: 'securityreportnovulns',
    is_manifest_list: false,
    last_modified: 'Thu, 02 Jun 2022 19:12:32 -0000',
    size: 100,
    manifest_digest:
      'sha256:securityreportnovulns3de5f80a38f65a85e709b77fd24491253990f30b6be',
    reversion: false,
    start_ts: 1654197152,
    manifest_list: undefined,
  },
  {
    name: 'securityreportmixedvulns',
    is_manifest_list: false,
    last_modified: 'Thu, 02 Jun 2022 19:12:32 -0000',
    size: 100,
    manifest_digest:
      'sha256:securityreportmixedvulns5f80a38f65a85e709b77fd24491253990f30b6be',
    reversion: false,
    start_ts: 1654197152,
    manifest_list: undefined,
  },
  {
    name: 'packagesreportnopackages',
    is_manifest_list: false,
    last_modified: 'Thu, 02 Jun 2022 19:12:32 -0000',
    size: 100,
    manifest_digest:
      'sha256:packagesreportnopackages5f80a38f65a85e709b77fd24491253990f30b6be',
    reversion: false,
    start_ts: 1654197152,
    manifest_list: undefined,
  },
];

const specificTagPathRegex = new RegExp(
  `/api/v1/repository/.+/.+/tag/?.+&specificTag=.+`,
);
mock.onGet(specificTagPathRegex).reply((request: AxiosRequestConfig) => {
  const searchParams = new URLSearchParams(request.url);
  const tagResponse: TagsResponse = {
    page: 1,
    has_additional: false,
    tags: tags.filter((tag) => tag.name === searchParams.get('specificTag')),
  };
  return [200, tagResponse];
});

const tagPathRegex = new RegExp(
  `/api/v1/repository/.+/.+/tag/\\?.+onlyActiveTags=true$`,
);
mock.onGet(tagPathRegex).reply((request: AxiosRequestConfig) => {
  return [
    200,
    {
      page: 1,
      has_additional: false,
      tags: tags,
    },
  ];
});

const deleteTagRegex = new RegExp(`/api/v1/repository/.+/.+/tag/.+`);
mock.onDelete(deleteTagRegex).reply((request: AxiosRequestConfig) => {
  const tagName: string = request.url.split('/').pop();
  tags = tags.filter((tag) => tag.name !== tagName);
  return [204, {}];
});
