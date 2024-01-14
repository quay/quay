import {Spinner} from '@patternfly/react-core';
import {
  ExpandableRowContent,
  Table,
  Thead,
  Tr,
  Th,
  Tbody,
  Td,
} from '@patternfly/react-table';
import prettyBytes from 'pretty-bytes';
import {useState} from 'react';
import {Tag, Manifest} from 'src/resources/TagResource';
import {useResetRecoilState} from 'recoil';
import {Link, useLocation} from 'react-router-dom';
import {getTagDetailPath} from 'src/routes/NavigationPath';
import TablePopover from './TablePopover';
import SecurityDetails from './SecurityDetails';
import {formatDate} from 'src/libs/utils';
import {SecurityDetailsState} from 'src/atoms/SecurityDetailsState';
import ColumnNames from './ColumnNames';
import {DownloadIcon} from '@patternfly/react-icons';
import {ChildManifestSize} from 'src/components/Table/ImageSize';
import TagActions from './TagsActions';
import {RepositoryDetails} from 'src/resources/RepositoryResource';
import Conditional from 'src/components/empty/Conditional';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import TagExpiration from './TagsTableExpiration';
import ManifestListSize from 'src/components/Table/ManifestListSize';

function SubRow(props: SubRowProps) {
  return (
    <Tr
      key={`${props.manifest.platform.os}-${props.manifest.platform.architecture}-${props.rowIndex}`}
      isExpanded={props.isTagExpanded(props.tag)}
    >
      <Td />
      {props.manifest.platform ? (
        <Td dataLabel="platform" noPadding={false} colSpan={2}>
          <ExpandableRowContent>
            <Link
              to={getTagDetailPath(
                location.pathname,
                props.org,
                props.repo,
                props.tag.name,
                new Map([['digest', props.manifest.digest]]),
              )}
            >
              {`${props.manifest.platform.os} on ${props.manifest.platform.architecture}`}
            </Link>
          </ExpandableRowContent>
        </Td>
      ) : (
        <Td />
      )}
      <Td dataLabel="security" noPadding={false} colSpan={1}>
        <ExpandableRowContent>
          <SecurityDetails
            org={props.org}
            repo={props.repo}
            digest={props.manifest.digest}
            tag={props.tag.name}
            variant="condensed"
          />
        </ExpandableRowContent>
      </Td>
      <Td dataLabel="size" noPadding={false} colSpan={3}>
        <ExpandableRowContent>
          <ChildManifestSize
            org={props.org}
            repo={props.repo}
            digest={props.manifest.digest}
          />
        </ExpandableRowContent>
      </Td>
      {props.manifest.digest ? (
        <Td dataLabel="digest" noPadding={false} colSpan={1}>
          <ExpandableRowContent>
            {props.manifest.digest.substring(0, 19)}
          </ExpandableRowContent>
        </Td>
      ) : (
        <Td />
      )}
    </Tr>
  );
}

function TagsTableRow(props: RowProps) {
  const config = useQuayConfig();
  const tag = props.tag;
  const rowIndex = props.rowIndex;

  // Reset SecurityDetailsState so that loading skeletons appear when viewing report
  const emptySecurityDetails = useResetRecoilState(SecurityDetailsState);
  const resetSecurityDetails = () => emptySecurityDetails();

  const location = useLocation();

  return (
    <Tbody
      data-testid="table-entry"
      key={tag.name}
      isExpanded={props.isTagExpanded(tag)}
    >
      <Tr>
        <Td
          expand={
            tag.is_manifest_list
              ? {
                  rowIndex,
                  isExpanded: props.isTagExpanded(tag),
                  onToggle: () =>
                    props.setTagExpanded(tag, !props.isTagExpanded(tag)),
                }
              : undefined
          }
        />
        <Td
          select={{
            rowIndex,
            onSelect: (_event, isSelecting) =>
              props.selectTag(tag, rowIndex, isSelecting),
            isSelected: props.selectedTags.includes(tag.name),
          }}
        />
        <Td dataLabel={ColumnNames.name}>
          <Link
            to={getTagDetailPath(
              location.pathname,
              props.org,
              props.repo,
              tag.name,
            )}
            onClick={resetSecurityDetails}
          >
            {tag.name}
          </Link>
        </Td>
        <Td dataLabel={ColumnNames.security}>
          {tag.is_manifest_list ? (
            'See Child Manifests'
          ) : (
            <SecurityDetails
              org={props.org}
              repo={props.repo}
              digest={tag.manifest_digest}
              tag={tag.name}
              variant="condensed"
            />
          )}
        </Td>
        <Td dataLabel={ColumnNames.size}>
          {tag.manifest_list ? (
            <ManifestListSize manifests={tag.manifest_list.manifests} />
          ) : (
            prettyBytes(tag.size)
          )}
        </Td>
        <Td dataLabel={ColumnNames.lastModified}>
          {formatDate(tag.last_modified)}
        </Td>
        <Td dataLabel={ColumnNames.expires}>
          <TagExpiration
            org={props.org}
            repo={props.repo}
            tag={tag.name}
            expiration={tag.expiration}
            loadTags={props.loadTags}
          />
        </Td>
        <Td dataLabel={ColumnNames.digest}>
          {tag.manifest_digest.substring(0, 19)}
        </Td>
        <Td
          dataLabel={ColumnNames.pull}
          style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
          }}
        >
          <TablePopover
            org={props.org}
            repo={props.repo}
            tag={tag.name}
            digest={tag.manifest_digest}
          >
            <DownloadIcon />
          </TablePopover>
        </Td>
        <Conditional
          if={
            props.repoDetails?.can_write &&
            config?.registry_state !== 'readonly'
          }
        >
          <Td>
            <TagActions
              org={props.org}
              repo={props.repo}
              manifest={tag.manifest_digest}
              tags={[tag.name]}
              expiration={tag.expiration}
              loadTags={props.loadTags}
              repoDetails={props.repoDetails}
            />
          </Td>
        </Conditional>
      </Tr>
      {tag.manifest_list
        ? tag.manifest_list.manifests.map((manifest, rowIndex) => (
            <SubRow
              key={rowIndex}
              org={props.org}
              repo={props.repo}
              tag={tag}
              rowIndex={rowIndex}
              manifest={manifest}
              isTagExpanded={props.isTagExpanded}
            />
          ))
        : null}
    </Tbody>
  );
}

export default function TagsTable(props: TableProps) {
  // Control expanded tags
  const [expandedTags, setExpandedTags] = useState<string[]>([]);
  const setTagExpanded = (tag: Tag, isExpanding = true) =>
    setExpandedTags((prevExpanded) => {
      // If expanding, add tag name to list otherwise return list without tag name
      // Filter accounts for cases where tag name is already in list when isExpanding == true
      const otherExpandedtagNames = prevExpanded.filter((r) => r !== tag.name);
      return isExpanding
        ? [...otherExpandedtagNames, tag.name]
        : otherExpandedtagNames;
    });
  const isTagExpanded = (tag: Tag) => expandedTags.includes(tag.name);

  return (
    <>
      <Table
        id="tag-list-table"
        aria-label="Expandable table"
        variant="compact"
      >
        <Thead>
          <Tr>
            <Th />
            <Th />
            <Th>Tag</Th>
            <Th>Security</Th>
            <Th>Size</Th>
            <Th>Last Modified</Th>
            <Th>Expires</Th>
            <Th>Manifest</Th>
            <Th>Pull</Th>
            <Th />
          </Tr>
        </Thead>
        {props.tags.map((tag: Tag, rowIndex: number) => (
          <TagsTableRow
            key={rowIndex}
            org={props.org}
            repo={props.repo}
            tag={tag}
            rowIndex={rowIndex}
            selectedTags={props.selectedTags}
            isTagExpanded={isTagExpanded}
            setTagExpanded={setTagExpanded}
            selectTag={props.selectTag}
            loadTags={props.loadTags}
            repoDetails={props.repoDetails}
          />
        ))}
      </Table>

      {props.loading ? <Spinner size="lg" /> : null}
      {props.tags.length == 0 && !props.loading ? (
        <div>This repository is empty.</div>
      ) : null}
    </>
  );
}

interface TableProps {
  org: string;
  repo: string;
  tags: Tag[];
  loading: boolean;
  selectAllTags: (isSelecting: boolean) => void;
  selectedTags: string[];
  selectTag: (tag: Tag, rowIndex?: number, isSelecting?: boolean) => void;
  loadTags: () => void;
  repoDetails: RepositoryDetails;
}

interface RowProps {
  org: string;
  repo: string;
  tag: Tag;
  rowIndex: number;
  selectedTags: string[];
  isTagExpanded: (tag: Tag) => boolean;
  setTagExpanded: (tag: Tag, isExpanding?: boolean) => void;
  selectTag: (tag: Tag, rowIndex?: number, isSelecting?: boolean) => void;
  loadTags: () => void;
  repoDetails: RepositoryDetails;
}

interface SubRowProps {
  org: string;
  repo: string;
  tag: Tag;
  rowIndex: number;
  manifest: Manifest;
  isTagExpanded: (tag: Tag) => boolean;
}
