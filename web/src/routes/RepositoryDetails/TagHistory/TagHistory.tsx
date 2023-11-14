import {useMemo, useState} from 'react';
import {Spinner} from '@patternfly/react-core';
import {Table, Thead, Tr, Th, Tbody, Td} from '@patternfly/react-table';
import {useAllTags} from 'src/hooks/UseTags';
import {Tag} from 'src/resources/TagResource';
import {formatDate, isNullOrUndefined} from 'src/libs/utils';
import {RepositoryDetails} from 'src/resources/RepositoryResource';
import Conditional from 'src/components/empty/Conditional';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import RestoreTag from './TagHistoryRestoreTag';
import {TagAction, TagEntry} from './types';
import TagActionDescription from './TagHistoryTagActionDescription';
import PermanentlyDeleteTag from './TagHistoryPermanentlyDeleteTag';
import TagHistoryToolBar from './TagHistoryToolbar';
import RequestError from 'src/components/errors/RequestError';

export default function TagHistory(props: TagHistoryProps) {
  const quayConfig = useQuayConfig();
  const [showFuture, setShowFuture] = useState<boolean>(false);
  const [query, setQuery] = useState<string>('');
  const [startTime, setStartTime] = useState<Date>(null);
  const [endTime, setEndTime] = useState<Date>(null);
  const {tags, loadingTags, errorLoadingTags, lastUpdated} = useAllTags(
    props.org,
    props.repo,
  );
  const [page, setPage] = useState<number>(1);
  const [perPage, setPerPage] = useState<number>(20);

  // Memo these to prevent recalculating on every render
  const {tagList, tagEntries} = useMemo(
    () => processTags(tags, showFuture),
    [lastUpdated, showFuture],
  );
  const filteredTags = useMemo(() => {
    const fitleredByQuery: TagEntry[] = tagList.filter((tag) =>
      tag.tag.name.includes(query),
    );
    const filteredByStartTime: TagEntry[] = !isNullOrUndefined(startTime)
      ? fitleredByQuery.filter((tag) => tag.time >= startTime.getTime())
      : fitleredByQuery;
    const filteredByEndTime: TagEntry[] = !isNullOrUndefined(endTime)
      ? filteredByStartTime.filter((tag) => tag.time < endTime.getTime())
      : filteredByStartTime;
    return filteredByEndTime;
  }, [
    lastUpdated,
    showFuture,
    query,
    startTime?.getTime(),
    endTime?.getTime(),
  ]);
  const isReadOnlyMode: boolean =
    quayConfig?.config?.REGISTRY_STATE === 'readonly';

  const paginatedTags = filteredTags.slice(
    (page - 1) * perPage,
    page * perPage,
  );

  if (loadingTags) {
    return <Spinner size="md" />;
  }

  if (errorLoadingTags) {
    return <RequestError message="Unable to load tag history" />;
  }

  return (
    <>
      <TagHistoryToolBar
        showFuture={showFuture}
        setShowFuture={setShowFuture}
        query={query}
        setQuery={setQuery}
        startTime={startTime}
        setStartTime={setStartTime}
        endTime={endTime}
        setEndTime={setEndTime}
        page={page}
        setPage={setPage}
        perPage={perPage}
        setPerPage={setPerPage}
        total={isNullOrUndefined(tagList) ? 0 : tagList.length}
      />
      <Table aria-label="Tag history table" variant="compact">
        <Thead>
          <Tr>
            <Th>Tag change</Th>
            <Th>Modified date/time</Th>
            <Conditional if={!isReadOnlyMode && props.repoDetails?.can_write}>
              <Th>Revert</Th>
            </Conditional>
            <Conditional
              if={
                !isReadOnlyMode &&
                props.repoDetails?.can_write &&
                quayConfig?.config?.PERMANENTLY_DELETE_TAGS
              }
            >
              <Th>Permanently delete</Th>
            </Conditional>
          </Tr>
        </Thead>
        <Tbody id="tag-history-table">
          {paginatedTags.map((tagEntry) => (
            <Tr key={`${tagEntry.digest}-${tagEntry.action}-${tagEntry.time}`}>
              <Td data-label="tag-change">
                <TagActionDescription tagEntry={tagEntry} />
              </Td>
              <Td data-label="date-modified">
                {formatDate(tagEntry.time / 1000)}
              </Td>
              <Conditional if={!isReadOnlyMode && props.repoDetails?.can_write}>
                <Td data-label="restore-tag">
                  <Conditional if={!isFutureEntry(tagEntry)}>
                    <RestoreTag
                      org={props.org}
                      repo={props.repo}
                      tagEntry={tagEntry}
                    />
                  </Conditional>
                </Td>
              </Conditional>
              <Conditional
                if={
                  !isReadOnlyMode &&
                  props.repoDetails?.can_write &&
                  quayConfig?.config?.PERMANENTLY_DELETE_TAGS
                }
              >
                <Td data-label="permanently-delete-tag">
                  <Conditional
                    if={
                      !isFutureEntry(tagEntry) &&
                      [TagAction.Delete, TagAction.Revert].includes(
                        tagEntry.action,
                      ) &&
                      props.repoDetails?.tag_expiration_s > 0 &&
                      tagEntry.tag.end_ts >
                        new Date().getTime() / 1000 -
                          props.repoDetails?.tag_expiration_s &&
                      tagEntry.tag.end_ts < new Date().getTime() / 1000
                    }
                  >
                    <PermanentlyDeleteTag
                      org={props.org}
                      repo={props.repo}
                      tagEntry={tagEntry}
                    />
                  </Conditional>
                </Td>
              </Conditional>
            </Tr>
          ))}
        </Tbody>
      </Table>
    </>
  );
}

function processTags(tags: Tag[], showFuture: boolean) {
  const MOVE_THRESHOLD = 2;
  const tagList: TagEntry[] = [];
  const tagEntries: Map<string, TagEntry[]> = new Map();

  const addEntry = (
    tag: Tag,
    time: number,
    action: TagAction,
    digest: string = null,
    oldDigest: string = null,
  ) => {
    if (!showFuture && time && time * 1000 >= new Date().getTime()) {
      return;
    }
    const entry: TagEntry = {
      action: action,
      time: time * 1000,
      tag: tag,
      digest: digest != null ? digest : tag.manifest_digest,
      oldDigest: oldDigest,
    };
    tagList.push(entry);
    tagEntries.get(tag.name).push(entry);
  };

  const removeEntry = (tagEntry: TagEntry) => {
    tagList.splice(tagList.indexOf(tagEntry), 1);
    if (tagEntries.has(tagEntry.tag.name)) {
      tagEntries
        .get(tagEntry.tag.name)
        .splice(tagEntries.get(tagEntry.tag.name).indexOf(tagEntry), 1);
    }
  };

  for (const tag of tags) {
    // Permanently deleted tags have a start greater than their end
    // so let's remove them from the view
    if (tag.start_ts > tag.end_ts) {
      continue;
    }

    if (!tagEntries.has(tag.name)) {
      tagEntries.set(tag.name, []);
    }

    if (tag.end_ts !== null && tag.end_ts !== undefined) {
      const currentEntries: TagEntry[] = tagEntries.get(tag.name);
      const futureEntry: TagEntry =
        currentEntries.length > 0
          ? currentEntries[currentEntries.length - 1]
          : null;
      const futureTag: Tag = futureEntry !== null ? futureEntry.tag : null;
      if (
        futureEntry !== null &&
        futureTag.start_ts - tag.end_ts <= MOVE_THRESHOLD
      ) {
        removeEntry(futureEntry);
        addEntry(
          tag,
          tag.end_ts,
          futureTag.reversion ? TagAction.Revert : TagAction.Move,
          futureEntry.digest,
          tag.manifest_digest,
        );
      } else {
        addEntry(tag, tag.end_ts, TagAction.Delete);
      }
    }

    if (tag.start_ts !== null && tag.start_ts !== undefined) {
      addEntry(
        tag,
        tag.start_ts,
        tag.reversion ? TagAction.Recreate : TagAction.Create,
      );
    }
  }

  tagList.sort((a, b) => b.time - a.time);
  tagEntries.forEach((value, key) => value.sort((a, b) => b.time - a.time));
  return {tagList, tagEntries};
}

const isFutureEntry = (tagEntry: TagEntry) => {
  return tagEntry.time >= new Date().getTime();
};

interface TagHistoryProps {
  org: string;
  repo: string;
  repoDetails: RepositoryDetails;
}
