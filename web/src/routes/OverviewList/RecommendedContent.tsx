import {
  Card,
  Button,
  Title,
  DataList,
  DataListItem,
  DataListItemRow,
  DataListItemCells,
  DataListCell,
  Label,
  Level,
  LevelItem,
  Split,
  SplitItem,
} from '@patternfly/react-core';
import {ArrowRightIcon, ExternalLinkAltIcon} from '@patternfly/react-icons';

export default function RecommendedContent() {
  return (
    <Card style={{margin: '24px'}}>
      <DataList aria-label="Recommended content">
        <DataListItem>
          <Level
            style={{
              minHeight: '72px',
              paddingLeft: '24px',
              paddingRight: '24px',
            }}
          >
            <LevelItem>
              <Title headingLevel="h4">Getting started with Quay.io</Title>
            </LevelItem>

            <LevelItem>
              <Label color="orange">Documentation</Label>
            </LevelItem>

            <LevelItem>
              <Button
                variant="link"
                component="a"
                href="https://docs.projectquay.io/quay_io.html"
              >
                View Documentation <ExternalLinkAltIcon />
              </Button>
            </LevelItem>
          </Level>
        </DataListItem>

        <DataListItem>
          <Level
            style={{
              minHeight: '72px',
              paddingLeft: '24px',
              paddingRight: '24px',
            }}
          >
            <LevelItem style={{alignSelf: 'center'}}>
              <Title headingLevel="h4">Create your repository</Title>
            </LevelItem>

            <LevelItem style={{textAlign: 'center'}}>
              <Label color="green">Quick Start</Label>
            </LevelItem>

            <LevelItem style={{textAlign: 'right'}}>
              <Button
                variant="link"
                component="a"
                href="https://quay.io/repository/"
              >
                Go to repositories <ArrowRightIcon />
              </Button>
            </LevelItem>
          </Level>
        </DataListItem>
      </DataList>
    </Card>
  );
}
