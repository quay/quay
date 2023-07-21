import {mock} from 'src/tests/fake-db/MockAxios';
import {LabelsResponse} from 'src/resources/TagResource';

const labelsResponse: LabelsResponse = {
  labels: [
    {
      id: '5bebb8a4-e917-4d99-89ac-gdfgdg3434g1',
      key: 'description',
      value: 'This is an example description label',
      source_type: 'manifest',
      media_type: 'text/plain',
    },
    {
      id: 'ff31310a-5857-4e7b-bcd4-vdfbdfgerge2',
      key: 'maintainer',
      value: 'maintainer@test.io',
      source_type: 'manifest',
      media_type: 'text/plain',
    },
    {
      id: '01c77159-da60-49ff-9cc3-vdfbdfgerge3',
      key: 'name',
      value: 'testname',
      source_type: 'manifest',
      media_type: 'text/plain',
    },
    {
      id: 'ec2eaea2-e62f-4e49-93a5-vdfbdfgerge4',
      key: 'release',
      value: '1',
      source_type: 'manifest',
      media_type: 'text/plain',
    },
    {
      id: '144d0215-8340-4377-a201-vdfbdfgerge5',
      key: 'summary',
      value: 'Example docker image',
      source_type: 'manifest',
      media_type: 'text/plain',
    },
    {
      id: 'd710893b-c0af-45ba-9ee4-vdfbdfgerge6',
      key: 'vendor',
      value: 'Redhat',
      source_type: 'manifest',
      media_type: 'text/plain',
    },
    {
      id: 'defcb097-8326-432b-a4d2-vdfbdfgerge7',
      key: 'version',
      value: '1.0.0',
      source_type: 'manifest',
      media_type: 'text/plain',
    },
  ],
};

const tagPathRegex = new RegExp(`/api/v1/repository/.+/.+/manifest/.+/label`);
mock.onGet(tagPathRegex).reply(() => {
  return [200, labelsResponse];
});
