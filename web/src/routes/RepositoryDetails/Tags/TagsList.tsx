import {TagsToolbar} from './TagsToolbar';
import TagsTable from './TagsTable';
import {useState, useEffect} from 'react';
import {
  searchTagsFilterState,
  searchTagsState,
  selectedTagsState,
} from 'src/atoms/TagListState';
import {
  Page,
  PageSection,
  PageSectionVariants,
  PanelFooter,
} from '@patternfly/react-core';
import {useRecoilState, useRecoilValue, useResetRecoilState} from 'recoil';
import {
  Tag,
  TagsResponse,
  getTags,
  getManifestByDigest,
  ManifestByDigestResponse,
} from 'src/resources/TagResource';
import {addDisplayError, isErrorString} from 'src/resources/ErrorHandling';
import ErrorBoundary from 'src/components/errors/ErrorBoundary';
import RequestError from 'src/components/errors/RequestError';
import Empty from 'src/components/empty/Empty';
import {CubesIcon} from '@patternfly/react-icons';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';
import {RepositoryDetails} from 'src/resources/RepositoryResource';

export default function TagsList(props: TagsProps) {
  const [tags, setTags] = useState<Tag[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [err, setErr] = useState<string>();
  const resetSelectedTags = useResetRecoilState(selectedTagsState);
  const searchFilter = useRecoilValue(searchTagsFilterState);
  const resetSearch = useResetRecoilState(searchTagsState);

  const filteredTags: Tag[] = searchFilter ? tags.filter(searchFilter) : tags;

  // Pagination related states
  const [perPage, setPerPage] = useState<number>(10);
  const [page, setPage] = useState<number>(1);
  const paginatedTags: Tag[] = filteredTags.slice(
    (page - 1) * perPage,
    page * perPage,
  );

  // Control selected tags
  const [selectedTags, setSelectedTags] = useRecoilState(selectedTagsState);
  const selectAllTags = (isSelecting = true) => {
    setSelectedTags(isSelecting ? tags.map((t) => t.name) : []);
  };
  const selectTag = (tag: Tag, rowIndex = 0, isSelecting = true) =>
    setSelectedTags((prevSelected) => {
      const otherSelectedtagNames = prevSelected.filter((r) => r !== tag.name);
      return isSelecting
        ? [...otherSelectedtagNames, tag.name]
        : otherSelectedtagNames;
    });

  const loadTags = async () => {
    const getManifest = async (tag: Tag) => {
      const manifestResp: ManifestByDigestResponse = await getManifestByDigest(
        props.organization,
        props.repository,
        tag.manifest_digest,
      );
      tag.manifest_list = JSON.parse(manifestResp.manifest_data);
    };
    let page = 1;
    let hasAdditional = false;
    try {
      do {
        const resp: TagsResponse = await getTags(
          props.organization,
          props.repository,
          page,
        );
        await Promise.all(
          resp.tags.map((tag: Tag) =>
            tag.is_manifest_list ? getManifest(tag) : null,
          ),
        );
        if (page == 1) {
          setTags(resp.tags);
        } else {
          setTags((currentTags) => [...currentTags, ...resp.tags]);
        }
        hasAdditional = resp.has_additional;
        page++;
        setLoading(false);
      } while (hasAdditional);
    } catch (error: any) {
      console.error(error);
      setLoading(false);
      setErr(addDisplayError('Unable to get tags', error));
    }
  };

  useEffect(() => {
    resetSearch();
    resetSelectedTags();
    loadTags();
  }, []);

  if (!loading && !tags?.length && !isErrorString(err)) {
    return (
      <Empty
        title="There are no viewable tags for this repository"
        icon={CubesIcon}
        body="No tags have been pushed to this repository. If you have the correct permissions, you may push tags to this repository."
      />
    );
  }

  return (
    <Page>
      <PageSection variant={PageSectionVariants.light}>
        <ErrorBoundary
          hasError={isErrorString(err)}
          fallback={<RequestError message={err} />}
        >
          <TagsToolbar
            organization={props.organization}
            repository={props.repository}
            tagCount={filteredTags.length}
            loadTags={loadTags}
            TagList={filteredTags}
            paginatedTags={paginatedTags}
            perPage={perPage}
            page={page}
            setPage={setPage}
            setPerPage={setPerPage}
            selectTag={selectTag}
            repoDetails={props.repoDetails}
          />
          <TagsTable
            org={props.organization}
            repo={props.repository}
            tags={paginatedTags}
            loading={loading}
            selectAllTags={selectAllTags}
            selectedTags={selectedTags}
            selectTag={selectTag}
            loadTags={loadTags}
            repoDetails={props.repoDetails}
          />
        </ErrorBoundary>
        <PanelFooter>
          <ToolbarPagination
            itemsList={filteredTags}
            perPage={perPage}
            page={page}
            setPage={setPage}
            setPerPage={setPerPage}
            bottom={true}
          />
        </PanelFooter>
      </PageSection>
    </Page>
  );
}

type TagsProps = {
  organization: string;
  repository: string;
  repoDetails: RepositoryDetails;
};
