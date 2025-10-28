import {Spinner, Tooltip} from '@patternfly/react-core';
import {
  ExpandableRowContent,
  Table,
  Thead,
  Tr,
  Th,
  ThProps,
  Tbody,
  Td,
} from '@patternfly/react-table';
import prettyBytes from 'pretty-bytes';
import {useState} from 'react';
import {Tag, Manifest, Label} from 'src/resources/TagResource';
import {useRecoilValue, useResetRecoilState} from 'recoil';
import {Link, useLocation} from 'react-router-dom';
import {getTagDetailPath} from 'src/routes/NavigationPath';
import TablePopover from './TablePopover';
import SecurityDetails from './SecurityDetails';
import {formatDate} from 'src/libs/utils';
import {SecurityDetailsState} from 'src/atoms/SecurityDetailsState';
import {expandedViewState} from 'src/atoms/TagListState';
import ColumnNames from './ColumnNames';
import {
  DownloadIcon,
  ShieldAltIcon,
  TagIcon,
  CubeIcon,
} from '@patternfly/react-icons';
import {ChildManifestSize} from 'src/components/Table/ImageSize';
import Labels from 'src/components/labels/Labels';
import TagActions from './TagsActions';
import {RepositoryDetails} from 'src/resources/RepositoryResource';
import Conditional from 'src/components/empty/Conditional';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {useQuayState} from 'src/hooks/UseQuayState';
import ManifestListSize from 'src/components/Table/ManifestListSize';
import {useTagPullStatistics} from 'src/hooks/UseTags';
import TagExpiration from './TagsTableExpiration';

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
      <Conditional if={props.config?.features?.SECURITY_SCANNER}>
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
      </Conditional>
      <Td dataLabel="size" noPadding={false} colSpan={1}>
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
      <Td
        colSpan={
          (props.config?.features?.IMAGE_PULL_STATS ? 4 : 2) +
          (props.config?.features?.SECURITY_SCANNER ? 0 : 1)
        }
      />
    </Tr>
  );
}

function TagsTableRow(props: RowProps) {
  const {inReadOnlyMode} = useQuayState();
  const config = useQuayConfig();
  const tag = props.tag;
  const rowIndex = props.rowIndex;
  const expandedView = useRecoilValue(expandedViewState);

  // Reset SecurityDetailsState so that loading skeletons appear when viewing report
  const emptySecurityDetails = useResetRecoilState(SecurityDetailsState);
  const resetSecurityDetails = () => emptySecurityDetails();

  const location = useLocation();

  // Calculate colspan dynamically based on whether actions column and pull stats columns are shown
  // Columns: expand(1) + select(1) + tag(1) + security(0-1) + size(1) + lastModified(1) + expires(1) + manifest(1) + pull(1) + pullStats(0-2) + actions(0-1)
  // Expanded row content spans all except first two (expand + select)
  const hasActions = !inReadOnlyMode && props.repoDetails?.can_write;
  const hasPullStats = config?.features?.IMAGE_PULL_STATS;
  const hasSecurity = config?.features?.SECURITY_SCANNER;
  const expandedColspan =
    7 + (hasPullStats ? 2 : 0) + (hasActions ? 1 : 0) - (hasSecurity ? 0 : 1);

  // Fetch pull statistics for this specific tag
  const {
    pullStatistics,
    isLoading: isLoadingPullStats,
    isError: isErrorPullStats,
  } = useTagPullStatistics(
    props.org,
    props.repo,
    tag.name,
    config?.features?.IMAGE_PULL_STATS || false,
  );

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
          {tag.cosign_signature_tag && (
            <Tooltip content="This tag has been signed via cosign.">
              <ShieldAltIcon
                style={{marginLeft: '8px'}}
                aria-label="Cosign signed"
              />
            </Tooltip>
          )}
        </Td>
        <Conditional if={config?.features?.SECURITY_SCANNER}>
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
        </Conditional>
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
        <Conditional if={config?.features?.IMAGE_PULL_STATS}>
          <Td dataLabel={ColumnNames.lastPulled}>
            {isLoadingPullStats ? (
              <Spinner size="sm" />
            ) : isErrorPullStats ? (
              'Error'
            ) : pullStatistics?.last_tag_pull_date ? (
              formatDate(pullStatistics.last_tag_pull_date)
            ) : (
              'Never'
            )}
          </Td>
          <Td dataLabel={ColumnNames.pullCount}>
            {isLoadingPullStats ? (
              <Spinner size="sm" />
            ) : isErrorPullStats ? (
              '-'
            ) : (
              pullStatistics?.tag_pull_count ?? 0
            )}
          </Td>
        </Conditional>
        <Td
          dataLabel={ColumnNames.pull}
          style={{
            display: 'flex',
            justifyContent: 'flex-start',
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
        <Conditional if={props.repoDetails?.can_write && !inReadOnlyMode}>
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
              config={config}
            />
          ))
        : null}
      {expandedView && (
        <Tr className="expanded-row">
          <Td />
          <Td colSpan={expandedColspan}>
            <div className="expanded-row-content">
              <div className="expanded-row-section">
                <Tooltip content="Manifest">
                  <CubeIcon style={{marginRight: '8px'}} />
                </Tooltip>
                <Tooltip content="The content-addressable SHA256 hash of this tag">
                  <span className="manifest-link">
                    <span className="id-label">SHA256</span>{' '}
                    <Link
                      to={getTagDetailPath(
                        location.pathname,
                        props.org,
                        props.repo,
                        tag.name,
                        new Map([['tab', 'layers']]),
                      )}
                    >
                      {tag.manifest_digest.substring(
                        'sha256:'.length,
                        'sha256:'.length + 12,
                      )}
                    </Link>
                  </span>
                </Tooltip>
              </div>
              <div className="expanded-row-section">
                <Tooltip content="Labels">
                  <TagIcon style={{marginRight: '8px'}} />
                </Tooltip>
                <Labels
                  org={props.org}
                  repo={props.repo}
                  digest={tag.manifest_digest}
                  cache={props.labelCache}
                  setCache={props.setLabelCache}
                />
              </div>
              {tag.cosign_signature_tag && (
                <div className="expanded-row-section">
                  <Tooltip content="Cosign Signature">
                    <ShieldAltIcon style={{marginRight: '8px'}} />
                  </Tooltip>
                  <Tooltip content="The artifact containing the cosign signature for this tag">
                    <span className="manifest-link">
                      <span className="id-label">cosign</span>{' '}
                      <Link
                        to={getTagDetailPath(
                          location.pathname,
                          props.org,
                          props.repo,
                          tag.cosign_signature_tag,
                          new Map([['tab', 'layers']]),
                        )}
                      >
                        {tag.cosign_signature_tag}
                      </Link>
                    </span>
                  </Tooltip>
                </div>
              )}
            </div>
          </Td>
          <Conditional if={props.repoDetails?.can_write && !inReadOnlyMode}>
            <Td />
          </Conditional>
        </Tr>
      )}
    </Tbody>
  );
}

export default function TagsTable(props: TableProps) {
  const config = useQuayConfig();

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
            <Th modifier="wrap" sort={props.getSortableSort?.(2)}>
              Tag
            </Th>
            <Conditional if={config?.features?.SECURITY_SCANNER}>
              <Th modifier="wrap">Security</Th>
            </Conditional>
            <Th modifier="wrap" sort={props.getSortableSort?.(4)}>
              Size
            </Th>
            <Th modifier="wrap" sort={props.getSortableSort?.(5)}>
              Last Modified
            </Th>
            <Th modifier="wrap" sort={props.getSortableSort?.(6)}>
              Expires
            </Th>
            <Th modifier="wrap" sort={props.getSortableSort?.(7)}>
              Manifest
            </Th>
            <Conditional if={config?.features?.IMAGE_PULL_STATS}>
              <Th modifier="wrap" sort={props.getSortableSort?.(8)}>
                Last Pulled
              </Th>
              <Th modifier="wrap" sort={props.getSortableSort?.(9)}>
                Pull Count
              </Th>
            </Conditional>
            <Th modifier="wrap">Pull</Th>
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
            labelCache={props.labelCache}
            setLabelCache={props.setLabelCache}
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
  getSortableSort?: (columnIndex: number) => ThProps['sort'];
  labelCache?: Record<string, Label[]>;
  setLabelCache?: (cache: Record<string, Label[]>) => void;
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
  labelCache?: Record<string, Label[]>;
  setLabelCache?: (cache: Record<string, Label[]>) => void;
}

interface SubRowProps {
  org: string;
  repo: string;
  tag: Tag;
  rowIndex: number;
  manifest: Manifest;
  isTagExpanded: (tag: Tag) => boolean;
  config: {
    features?: {
      IMAGE_PULL_STATS?: boolean;
    };
  } | null;
}
