import {
  PageSection,
  PageSectionVariants,
  PanelFooter,
} from '@patternfly/react-core';
import {CubesIcon} from '@patternfly/react-icons';
import {useEffect, useState} from 'react';
import {useRecoilState, useRecoilValue, useResetRecoilState} from 'recoil';
import {
  searchTagsFilterState,
  searchTagsState,
  selectedTagsState,
  showSignaturesState,
} from 'src/atoms/TagListState';
import Empty from 'src/components/empty/Empty';
import ErrorBoundary from 'src/components/errors/ErrorBoundary';
import RequestError from 'src/components/errors/RequestError';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';
import {addDisplayError, isErrorString} from 'src/resources/ErrorHandling';
import {RepositoryDetails} from 'src/resources/RepositoryResource';
import {
  ManifestByDigestResponse,
  Tag,
  TagsResponse,
  getManifestByDigest,
  getTags,
} from 'src/resources/TagResource';
import TagsTable from './TagsTable';
import {TagsToolbar} from './TagsToolbar';
import {usePaginatedSortableTable} from '../../../hooks/usePaginatedSortableTable';
import {enrichTagsWithCosignData, isCosignSignatureTag} from 'src/libs/cosign';

export default function TagsList(props: TagsProps) {
  const [tags, setTags] = useState<Tag[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [err, setErr] = useState<string>();
  const resetSelectedTags = useResetRecoilState(selectedTagsState);
  const searchFilter = useRecoilValue(searchTagsFilterState);
  const resetSearch = useResetRecoilState(searchTagsState);
  const showSignatures = useRecoilValue(showSignaturesState);

  // Filter out signature tags if showSignatures is false
  const filteredTags = showSignatures
    ? tags
    : tags.filter((tag) => !isCosignSignatureTag(tag.name));

  // Use unified table hook for sorting, filtering, and pagination
  const {
    paginatedData: paginatedTags,
    sortedData: sortedTags,
    getSortableSort,
    paginationProps,
  } = usePaginatedSortableTable(filteredTags, {
    columns: {
      2: (item: Tag) => item.name, // Tag Name
      4: (item: Tag) => item.size || 0, // Size
      5: (item: Tag) => item.last_modified, // Last Modified
      6: (item: Tag) => item.expiration || '', // Expires
      7: (item: Tag) => item.manifest_digest, // Manifest
    },
    filter: searchFilter,
    initialPerPage: 20,
  });

  // Control selected tags
  const [selectedTags, setSelectedTags] = useRecoilState(selectedTagsState);
  const selectAllTags = (isSelecting = true) => {
    setSelectedTags(isSelecting ? sortedTags.map((t) => t.name) : []);
  };
  const selectTag = (tag: Tag, rowIndex?: number, isSelecting = true) => {
    // rowIndex parameter is kept for interface compatibility but not used in this implementation
    setSelectedTags((prevSelected) => {
      const otherSelectedtagNames = prevSelected.filter((r) => r !== tag.name);
      return isSelecting
        ? [...otherSelectedtagNames, tag.name]
        : otherSelectedtagNames;
    });
  };

  const loadTags = async () => {
    const getManifest = async (tag: Tag) => {
      const manifestResp: ManifestByDigestResponse = await getManifestByDigest(
        props.organization,
        props.repository,
        tag.manifest_digest,
        true, // include_modelcard
      );
      tag.manifest_list = JSON.parse(manifestResp.manifest_data);
    };
    let page = 1;
    let hasAdditional = false;
    let allTags: Tag[] = [];
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
        allTags = page == 1 ? resp.tags : [...allTags, ...resp.tags];

        // Progressive rendering: update UI with tags as they load
        setTags(allTags);
        setLoading(false);

        hasAdditional = resp.has_additional;
        page++;
      } while (hasAdditional);
      // After all tags are loaded, enrich with Cosign signature data
      // This requires all tags to be present to build the signature map correctly
      const enrichedTags = enrichTagsWithCosignData(allTags);
      setTags(enrichedTags);
    } catch (error: unknown) {
      console.error(error);
      setLoading(false);
      setErr(addDisplayError('Unable to get tags', error as Error));
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
    <PageSection variant={PageSectionVariants.light}>
      <ErrorBoundary
        hasError={isErrorString(err)}
        fallback={<RequestError message={err} />}
      >
        <TagsToolbar
          organization={props.organization}
          repository={props.repository}
          tagCount={sortedTags.length}
          loadTags={loadTags}
          TagList={sortedTags}
          paginatedTags={paginatedTags}
          perPage={paginationProps.perPage}
          page={paginationProps.page}
          setPage={paginationProps.setPage}
          setPerPage={paginationProps.setPerPage}
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
          getSortableSort={getSortableSort}
        />
      </ErrorBoundary>
      <PanelFooter>
        <ToolbarPagination {...paginationProps} bottom={true} />
      </PanelFooter>
    </PageSection>
  );
}

type TagsProps = {
  organization: string;
  repository: string;
  repoDetails: RepositoryDetails;
};
