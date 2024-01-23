import {
  ClipboardCopy,
  DescriptionList,
  DescriptionListDescription,
  DescriptionListGroup,
  DescriptionListTerm,
  Divider,
  PageSection,
  PageSectionVariants,
  Skeleton,
} from '@patternfly/react-core';
import {ImageSize} from 'src/components/Table/ImageSize';
import Labels from 'src/components/labels/Labels';
import {formatDate} from 'src/libs/utils';
import {Tag} from 'src/resources/TagResource';
import SecurityDetails from 'src/routes/RepositoryDetails/Tags/SecurityDetails';
import CopyTags from './DetailsCopyTags';

export default function Details(props: DetailsProps) {
  return (
    <>
      <PageSection variant={PageSectionVariants.light}>
        <DescriptionList
          columnModifier={{
            default: '2Col',
          }}
          data-testid="tag-details"
        >
          <DescriptionListGroup data-testid="name">
            <DescriptionListTerm>Name</DescriptionListTerm>
            <DescriptionListDescription>
              {props.tag.name ? (
                props.tag.name
              ) : (
                <Skeleton width="100%"></Skeleton>
              )}
            </DescriptionListDescription>
          </DescriptionListGroup>
          <DescriptionListGroup data-testid="creation">
            <DescriptionListTerm>Creation</DescriptionListTerm>
            <DescriptionListDescription>
              {props.tag.start_ts ? (
                formatDate(props.tag.start_ts)
              ) : (
                <Skeleton width="100%"></Skeleton>
              )}
            </DescriptionListDescription>
          </DescriptionListGroup>
          <DescriptionListGroup data-testid="repository">
            <DescriptionListTerm>Repository</DescriptionListTerm>
            <DescriptionListDescription>
              {props.repo ? props.repo : <Skeleton width="100%"></Skeleton>}
            </DescriptionListDescription>
          </DescriptionListGroup>
          <DescriptionListGroup data-testid="modified">
            <DescriptionListTerm>Modified</DescriptionListTerm>
            <DescriptionListDescription>
              {props.tag.last_modified ? (
                formatDate(props.tag.last_modified)
              ) : (
                <Skeleton width="100%"></Skeleton>
              )}
            </DescriptionListDescription>
          </DescriptionListGroup>
          <DescriptionListGroup>
            <DescriptionListTerm>Digest</DescriptionListTerm>
            <DescriptionListDescription>
              {props.digest ? (
                <ClipboardCopy
                  data-testid="digest-clipboardcopy"
                  isReadOnly
                  hoverTip="Copy"
                  clickTip="Copied"
                  variant="inline-compact"
                >
                  {props.digest}
                </ClipboardCopy>
              ) : (
                <Skeleton width="100%"></Skeleton>
              )}
            </DescriptionListDescription>
          </DescriptionListGroup>
          <DescriptionListGroup data-testid="size">
            <DescriptionListTerm>Size</DescriptionListTerm>
            <DescriptionListDescription>
              {props.digest != '' ? (
                <ImageSize
                  org={props.org}
                  repo={props.repo}
                  digest={props.digest}
                />
              ) : (
                <Skeleton width="100%"></Skeleton>
              )}
            </DescriptionListDescription>
          </DescriptionListGroup>
          <DescriptionListGroup data-testid="vulnerabilities">
            <DescriptionListTerm>Vulnerabilities</DescriptionListTerm>
            <DescriptionListDescription>
              <SecurityDetails
                org={props.org}
                repo={props.repo}
                digest={props.digest}
                tag={props.tag.name}
                cacheResults={true}
              />
            </DescriptionListDescription>
          </DescriptionListGroup>
          <DescriptionListGroup data-testid="labels">
            <DescriptionListTerm>Labels</DescriptionListTerm>
            <DescriptionListDescription>
              {props.tag.manifest_digest !== '' ? (
                <Labels
                  org={props.org}
                  repo={props.repo}
                  digest={props.tag.manifest_digest}
                />
              ) : (
                <Skeleton width="100%"></Skeleton>
              )}
            </DescriptionListDescription>
          </DescriptionListGroup>
        </DescriptionList>
      </PageSection>
      <Divider />
      <PageSection variant={PageSectionVariants.light}>
        <CopyTags
          org={props.org}
          repo={props.repo}
          tag={props.tag.name}
          digest={props.digest}
        />
      </PageSection>
    </>
  );
}

type DetailsProps = {
  tag: Tag;
  org: string;
  repo: string;
  digest: string;
};
