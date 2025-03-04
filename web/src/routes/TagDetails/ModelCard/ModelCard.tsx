import {useEffect, useState} from 'react';
import {Card, PageSection, Divider, TextContent} from '@patternfly/react-core';
import {useLocation, useSearchParams} from 'react-router-dom';

import {Remark, useRemark} from 'react-remark';
import remarkGemoji from 'remark-gemoji';

import {
  ManifestByDigestResponse,
  Tag,
  TagsResponse,
  getManifestByDigest,
  getTags,
} from 'src/resources/TagResource';
import {
  parseOrgNameFromUrl,
  parseRepoNameFromUrl,
  parseTagNameFromUrl,
} from '../../../libs/utils';

export function ModelCard() {
  const [searchParams] = useSearchParams();
  const location = useLocation();

  const org = parseOrgNameFromUrl(location.pathname);
  const repo = parseRepoNameFromUrl(location.pathname);
  const tag = parseTagNameFromUrl(location.pathname);

  const [modelcardMarkdown, setModelcardMarkdown] = useState<string>('');

  useEffect(() => {
    (async () => {
      try {
        const resp: TagsResponse = await getTags(org, repo, 1, 100, tag);
        const tagResp: Tag = resp.tags[0];

        const manifestResp: ManifestByDigestResponse =
          await getManifestByDigest(org, repo, tagResp.manifest_digest, false);

        tagResp.manifest_list = JSON.parse(manifestResp.manifest_data);

        const markdown = manifestResp['modelcard'];
        setModelcardMarkdown(markdown);
      } catch (error: any) {
        console.error(error);
        setErr(addDisplayError('Unable to get details for tag', error));
      }
    })();
  }, []);

  return (
    <>
      <Divider />
      <PageSection>
        <TextContent>
          <Remark>{modelcardMarkdown}</Remark>
        </TextContent>
      </PageSection>
    </>
  );
}
