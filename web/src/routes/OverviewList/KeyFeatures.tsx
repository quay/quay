import {
  Card,
  Hint,
  HintBody,
  HintFooter,
  Button,
  ExpandableSection,
  DataList,
  DataListItem,
  Divider,
  Text,
  Flex,
  FlexItem,
  Icon,
} from '@patternfly/react-core';
import {
  BuildIcon,
  CloudSecurityIcon,
  DownloadIcon,
  ExternalLinkAltIcon,
  PrivateIcon,
} from '@patternfly/react-icons';
import './css/KeyFeatures.scss';

export default function KeyFeatures() {
  return (
    <div>
      <Card className="key-features" style={{margin: '24px'}}>
        <DataList aria-label="Key features">
          <DataListItem>
            <ExpandableSection
              toggleContent={
                <Flex>
                  <FlexItem>
                    <Icon size="lg">
                      {' '}
                      <PrivateIcon />{' '}
                    </Icon>
                  </FlexItem>
                  <Divider orientation={{default: 'vertical'}} />
                  <FlexItem className="key-feature">
                    {' '}
                    Store your containers securely
                  </FlexItem>
                </Flex>
              }
              displaySize="lg"
            >
              <Text>
                Ensure your apps are stored privately, with access that you
                control. Quay is teamwork optimized, with powerful access
                controls.
              </Text>
            </ExpandableSection>
          </DataListItem>

          <DataListItem>
            <ExpandableSection
              toggleContent={
                <Flex>
                  <FlexItem>
                    <Icon size="lg">
                      {' '}
                      <BuildIcon />{' '}
                    </Icon>
                  </FlexItem>
                  <Divider orientation={{default: 'vertical'}} />
                  <FlexItem className="key-feature">
                    Automated container build integration
                  </FlexItem>
                </Flex>
              }
              displaySize="lg"
            >
              <Text>
                Use Quay.io to automate your container builds, with integration
                to GitHub, Bitbucket, and more. Robot accounts allow you to lock
                down automated access and audit each deployment.
              </Text>
            </ExpandableSection>
          </DataListItem>

          <DataListItem>
            <ExpandableSection
              toggleContent={
                <Flex>
                  <FlexItem>
                    <Icon size="lg">
                      <CloudSecurityIcon />
                    </Icon>
                  </FlexItem>
                  <Divider orientation={{default: 'vertical'}} />
                  <FlexItem className="key-feature">
                    Continually scan your containers for vulnerabilities
                  </FlexItem>
                </Flex>
              }
              displaySize="lg"
            >
              <Text>
                Quay continually scans your containers for vulnerabilities,
                giving you complete visibility into known issues and how to fix
                them.
              </Text>
            </ExpandableSection>
          </DataListItem>

          <DataListItem>
            <ExpandableSection
              toggleContent={
                <Flex>
                  <FlexItem>
                    <Icon size="lg">
                      {' '}
                      <DownloadIcon />{' '}
                    </Icon>
                  </FlexItem>
                  <Divider orientation={{default: 'vertical'}} />
                  <FlexItem className="key-feature">
                    Free public download page for your container
                  </FlexItem>
                </Flex>
              }
              displaySize="lg"
            >
              <Text>
                {
                  "Provide a public download page for your container. The best part, they're free!"
                }
              </Text>
            </ExpandableSection>
          </DataListItem>
        </DataList>
      </Card>

      <Hint className="quayio-hint">
        <HintBody>
          Red Hat Quay.io container registry platform provides secure storage,
          distribution, and governance of containers and cloud native artifacts
          on any infrastructure. It is available as a standalone component or
          running on top of Red Hat Openshift.
        </HintBody>
        <HintFooter>
          <Button
            component="a"
            href="https://www.redhat.com/en/technologies/cloud-computing/quay"
            variant="link"
            isInline
            icon={<ExternalLinkAltIcon />}
          >
            Learn about on-prem Red Hat Quay
          </Button>
        </HintFooter>
      </Hint>
    </div>
  );
}
