import {Spinner} from '@patternfly/react-core';
import {
  ExpandableRowContent,
  TableComposable,
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
import {Link} from 'react-router-dom';
import {getTagDetailPath} from 'src/routes/NavigationPath';
import TablePopover from './TablePopover';
import SecurityDetails from './SecurityDetails';
import {formatDate} from 'src/libs/utils';
import {SecurityDetailsState} from 'src/atoms/SecurityDetailsState';
import ColumnNames from './ColumnNames';
import {DownloadIcon} from '@patternfly/react-icons';
import ImageSize from 'src/components/Table/ImageSize';

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
          <ImageSize
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

function Row(props: RowProps) {
  const tag = props.tag;
  const rowIndex = props.rowIndex;
  let size =
    typeof tag.manifest_list != 'undefined' ? 'N/A' : prettyBytes(tag.size);

  // Behavior taken from previous UI
  if (tag.size === 0) {
    size = 'Unknown';
  }

  // Reset SecurityDetailsState so that loading skeletons appear when viewing report
  const emptySecurityDetails = useResetRecoilState(SecurityDetailsState);
  const resetSecurityDetails = () => emptySecurityDetails();

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
            to={getTagDetailPath(props.org, props.repo, tag.name)}
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
        <Td dataLabel={ColumnNames.size}>{size}</Td>
        <Td dataLabel={ColumnNames.lastModified}>
          {formatDate(tag.last_modified)}
        </Td>
        <Td dataLabel={ColumnNames.expires}>{tag.expiration ?? 'Never'}</Td>
        <Td dataLabel={ColumnNames.manifest}>
          {tag.manifest_digest.substring(0, 19)}
        </Td>
        <Td dataLabel={ColumnNames.pull}>
          <TablePopover
            org={props.org}
            repo={props.repo}
            tag={tag.name}
            digest={tag.manifest_digest}
          >
            <DownloadIcon />
          </TablePopover>
        </Td>
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

export default function Table(props: TableProps) {
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
      <TableComposable aria-label="Expandable table">
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
          </Tr>
        </Thead>
        {props.tags.map((tag: Tag, rowIndex: number) => (
          <Row
            key={rowIndex}
            org={props.org}
            repo={props.repo}
            tag={tag}
            rowIndex={rowIndex}
            selectedTags={props.selectedTags}
            isTagExpanded={isTagExpanded}
            setTagExpanded={setTagExpanded}
            selectTag={props.selectTag}
          />
        ))}
      </TableComposable>

      {props.loading ? <Spinner isSVG size="lg" /> : null}
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
}

interface SubRowProps {
  org: string;
  repo: string;
  tag: Tag;
  rowIndex: number;
  manifest: Manifest;
  isTagExpanded: (tag: Tag) => boolean;
}
