import {Popover, ClipboardCopy, Content} from '@patternfly/react-core';
import {useRecoilState} from 'recoil';
import {currentOpenPopoverState} from 'src/atoms/TagListState';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';

export default function TablePopover(props: TablePopoverProps) {
  const [currentOpenPopover, setCurrentOpenPopover] = useRecoilState(
    currentOpenPopoverState,
  );

  const config = useQuayConfig();
  const domain = config?.config.SERVER_HOSTNAME;

  return (
    <Popover
      data-testid="pull-popover"
      isVisible={currentOpenPopover === props.tag}
      shouldClose={() => {
        setCurrentOpenPopover('');
      }}
      headerContent={<div>Fetch Tag</div>}
      bodyContent={
        <div>
          <Content component="p" style={{fontWeight: 'bold'}}>
            Image (By Tag)
          </Content>
          <ClipboardCopy
            data-testid="copy-tag"
            isReadOnly
            hoverTip="Copy"
            clickTip="Copied"
          >
            {`${domain}/${props.org}/${props.repo}:${props.tag}`}
          </ClipboardCopy>
          <br />
          <Content component="p" style={{fontWeight: 'bold'}}>
            Image (By Digest)
          </Content>
          <ClipboardCopy
            data-testid="copy-digest"
            isReadOnly
            hoverTip="Copy"
            clickTip="Copied"
          >
            {`${domain}/${props.org}/${props.repo}@${props.digest}`}
          </ClipboardCopy>
        </div>
      }
    >
      <div
        onMouseEnter={() => {
          setCurrentOpenPopover(props.tag);
        }}
      >
        {props.children}
      </div>
    </Popover>
  );
}

type TablePopoverProps = {
  org: string;
  repo: string;
  tag: string;
  digest: string;
  children: React.ReactNode;
};
