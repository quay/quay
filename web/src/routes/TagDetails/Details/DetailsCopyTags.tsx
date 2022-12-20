import {
  DescriptionList,
  DescriptionListTerm,
  DescriptionListGroup,
  DescriptionListDescription,
  ClipboardCopy,
  Title,
} from '@patternfly/react-core';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import './Details.css';

export default function CopyTags(props: CopyTagsProps) {
  const config = useQuayConfig();
  const domain = config?.config.SERVER_HOSTNAME;

  return (
    <>
      <Title headingLevel="h3" className="fetch-tags-title">
        Fetch Tag
      </Title>
      <DescriptionList data-testid="copy-pull-commands">
        <DescriptionListGroup>
          <DescriptionListTerm>Podman Pull (by tag)</DescriptionListTerm>
          <DescriptionListDescription>
            <ClipboardCopy
              data-testid="podman-tag-clipboardcopy"
              isReadOnly
              hoverTip="Copy"
              clickTip="Copied"
            >
              {`podman pull ${domain}/${props.org}/${props.repo}:${props.tag}`}
            </ClipboardCopy>
          </DescriptionListDescription>
        </DescriptionListGroup>
        <DescriptionListGroup>
          <DescriptionListTerm>Docker Pull (by tag)</DescriptionListTerm>
          <DescriptionListDescription>
            <ClipboardCopy
              data-testid="docker-tag-clipboardcopy"
              isReadOnly
              hoverTip="Copy"
              clickTip="Copied"
            >
              {`docker pull ${domain}/${props.org}/${props.repo}:${props.tag}`}
            </ClipboardCopy>
          </DescriptionListDescription>
        </DescriptionListGroup>
        <DescriptionListGroup>
          <DescriptionListTerm>Podman Pull (by digest)</DescriptionListTerm>
          <DescriptionListDescription>
            <ClipboardCopy
              data-testid="podman-digest-clipboardcopy"
              isReadOnly
              hoverTip="Copy"
              clickTip="Copied"
            >
              {`podman pull ${domain}/${props.org}/${props.repo}@${props.digest}`}
            </ClipboardCopy>
          </DescriptionListDescription>
        </DescriptionListGroup>
        <DescriptionListGroup>
          <DescriptionListTerm>Docker Pull (by digest)</DescriptionListTerm>
          <DescriptionListDescription>
            <ClipboardCopy
              data-testid="docker-digest-clipboardcopy"
              isReadOnly
              hoverTip="Copy"
              clickTip="Copied"
            >
              {`docker pull ${domain}/${props.org}/${props.repo}@${props.digest}`}
            </ClipboardCopy>
          </DescriptionListDescription>
        </DescriptionListGroup>
      </DescriptionList>
    </>
  );
}

type CopyTagsProps = {
  org: string;
  repo: string;
  tag: string;
  digest: string;
};
