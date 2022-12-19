import {
  Page,
  PageSection,
  PageSectionVariants,
  Title,
} from '@patternfly/react-core';
import {useSearchParams, useLocation} from 'react-router-dom';
import {useState, useEffect} from 'react';
import TagArchSelect from './TagDetailsArchSelect';
import TagTabs from './TagDetailsTabs';
import {
  TagsResponse,
  getTags,
  getManifestByDigest,
  Tag,
  ManifestByDigestResponse,
} from 'src/resources/TagResource';
import {addDisplayError, isErrorString} from 'src/resources/ErrorHandling';
import {QuayBreadcrumb} from 'src/components/breadcrumb/Breadcrumb';
import ErrorBoundary from 'src/components/errors/ErrorBoundary';
import RequestError from 'src/components/errors/RequestError';
import {useResetRecoilState} from 'recoil';
import {
  SecurityDetailsErrorState,
  SecurityDetailsState,
} from 'src/atoms/SecurityDetailsState';

export default function TagDetails() {
  const [searchParams] = useSearchParams();
  const [digest, setDigest] = useState<string>('');
  const [err, setErr] = useState<string>();
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
  const [org, ...repoPath] = location.pathname.split('/').slice(2);
  const tag = repoPath.pop();
  const repo = repoPath.join('/');

  useEffect(() => {
    (async () => {
      resetSecurityDetails();
      resetSecurityError();
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
        if (tagResp.is_manifest_list) {
          const manifestResp: ManifestByDigestResponse =
            await getManifestByDigest(org, repo, tagResp.manifest_digest);
          tagResp.manifest_list = JSON.parse(manifestResp.manifest_data);
        }

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
      } catch (error: any) {
        console.error(error);
        setErr(addDisplayError('Unable to get details for tag', error));
      }
    })();
  }, []);

  return (
    <Page>
      <QuayBreadcrumb />
      <PageSection
        variant={PageSectionVariants.light}
        className="no-padding-bottom"
      >
        <Title headingLevel="h1">{tag}</Title>
        <TagArchSelect
          digest={digest}
          options={tagDetails.manifest_list?.manifests}
          setDigest={setDigest}
          render={tagDetails.is_manifest_list}
        />
      </PageSection>
      <PageSection
        variant={PageSectionVariants.light}
        className="no-padding-on-sides"
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
            err={err}
          />
        </ErrorBoundary>
      </PageSection>
    </Page>
  );
}
