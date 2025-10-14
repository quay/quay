import {PageSection, PageSectionVariants, Title} from '@patternfly/react-core';
import {useEffect, useState} from 'react';
import {useLocation, useSearchParams} from 'react-router-dom';
import {useResetRecoilState} from 'recoil';
import {
  SecurityDetailsErrorState,
  SecurityDetailsState,
} from 'src/atoms/SecurityDetailsState';
import {QuayBreadcrumb} from 'src/components/breadcrumb/Breadcrumb';
import ErrorBoundary from 'src/components/errors/ErrorBoundary';
import RequestError from 'src/components/errors/RequestError';
import {addDisplayError, isErrorString} from 'src/resources/ErrorHandling';
import {
  ManifestByDigestResponse,
  Tag,
  TagsResponse,
  getManifestByDigest,
  getTags,
} from 'src/resources/TagResource';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {
  parseOrgNameFromUrl,
  parseRepoNameFromUrl,
  parseTagNameFromUrl,
} from '../../libs/utils';
import TagArchSelect from './TagDetailsArchSelect';
import TagTabs from './TagDetailsTabs';

export default function TagDetails() {
  const [searchParams] = useSearchParams();
  const [digest, setDigest] = useState<string>('');
  const [manifestData, setManifestData] =
    useState<ManifestByDigestResponse>(null);
  const [err, setErr] = useState<string>();
  const quayConfig = useQuayConfig();
  const resetSecurityDetails = useResetRecoilState(SecurityDetailsState);
  const resetSecurityError = useResetRecoilState(SecurityDetailsErrorState);
  const [tagDetails, setTagDetails] = useState<Tag>({
    name: '',
    is_manifest_list: false,
    last_modified: '',
    manifest_digest: '',
    reversion: false,
    size: 0,
    start_ts: 0,
    manifest_list: {
      schemaVersion: 0,
      mediaType: '',
      manifests: [],
    },
  });

  // TODO: refactor, need more checks when parsing path
  const location = useLocation();

  const org = parseOrgNameFromUrl(location.pathname);
  const repo = parseRepoNameFromUrl(location.pathname);
  const tag = parseTagNameFromUrl(location.pathname);

  useEffect(() => {
    resetSecurityDetails();
    resetSecurityError();
  }, [org, repo, tag]);

  useEffect(() => {
    (async () => {
      try {
        const resp: TagsResponse = await getTags(org, repo, 1, 100, tag);

        // These should never happen but checking for errors just in case
        if (resp.tags.length === 0) {
          throw new Error('Could not find tag');
        }
        if (resp.tags.length > 1) {
          throw new Error(
            'Unexpected response from API: more than one tag returned',
          );
        }

        const tagResp: Tag = resp.tags[0];

        // Always fetch manifest data for layers and other features, but
        // only include modelcard if UI_MODELCARD feature is enabled
        const includeModelcard = quayConfig?.features.UI_MODELCARD || false;
        const manifestResp: ManifestByDigestResponse =
          await getManifestByDigest(
            org,
            repo,
            tagResp.manifest_digest,
            includeModelcard,
          );

        if (tagResp.is_manifest_list) {
          tagResp.manifest_list = JSON.parse(manifestResp.manifest_data);
        }
        if (manifestResp.modelcard) {
          tagResp.modelcard = manifestResp.modelcard;
        }

        setManifestData(manifestResp);

        // Confirm requested digest exists for this tag
        const requestedDigest = searchParams.get('digest');
        if (
          requestedDigest &&
          requestedDigest !== tagResp.manifest_digest &&
          !tagResp.manifest_list?.manifests?.some(
            (m) => m.digest === requestedDigest,
          )
        ) {
          throw new Error(`Requested digest not found: ${requestedDigest}`);
        }

        let currentDigest =
          tagResp.is_manifest_list &&
          tagResp.manifest_list?.manifests?.length > 0
            ? tagResp.manifest_list.manifests[0].digest
            : tagResp.manifest_digest;
        currentDigest = searchParams.get('digest')
          ? searchParams.get('digest')
          : currentDigest;
        setDigest(currentDigest);
        setTagDetails(tagResp);
      } catch (error: unknown) {
        console.error(error);
        const errorObj =
          error instanceof Error ? error : new Error(String(error));
        setErr(addDisplayError('Unable to get details for tag', errorObj));
      }
    })();
  }, [org, repo, tag, searchParams, quayConfig?.features?.UI_MODELCARD]);

  return (
    <>
      <QuayBreadcrumb />
      <PageSection variant={PageSectionVariants.light}>
        <Title headingLevel="h1">
          {repo}:{tag}
        </Title>
        <TagArchSelect
          digest={digest}
          options={tagDetails.manifest_list?.manifests}
          setDigest={setDigest}
          render={tagDetails.is_manifest_list}
          style={{marginTop: 'var(--pf-v5-global--spacer--md)'}}
        />
      </PageSection>
      <PageSection
        variant={PageSectionVariants.light}
        padding={{default: 'noPadding'}}
      >
        <ErrorBoundary
          hasError={isErrorString(err)}
          fallback={<RequestError message={err} />}
        >
          <TagTabs
            org={org}
            repo={repo}
            tag={tagDetails}
            digest={digest}
            manifestData={manifestData}
            err={err}
          />
        </ErrorBoundary>
      </PageSection>
    </>
  );
}
