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
                    <Icon size="lg" id="store-containers-dropdown">
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
              <Text id="store-containers-info">
                Easily publish your container images or or store them privately
                with granular access control. Quay.io is optimized for open
                source project and enterprise users, with powerful flexible
                permission and tenancy model.
              </Text>
            </ExpandableSection>
          </DataListItem>

          <DataListItem>
            <ExpandableSection
              toggleContent={
                <Flex>
                  <FlexItem>
                    <Icon size="lg" id="build-containers-dropdown">
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
              <Text id="build-containers-info">
                Use Quay.io to automate your container builds, with integration
                to GitHub, GitLab, and more. Robot accounts allow you to lock
                down automated access and audit each deployment.
              </Text>
            </ExpandableSection>
          </DataListItem>

          <DataListItem>
            <ExpandableSection
              toggleContent={
                <Flex>
                  <FlexItem>
                    <Icon size="lg" id="scan-containers-dropdown">
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
              <Text id="scan-containers-info">
                Quay.io continually scans your containers for vulnerabilities,
                giving you real-time visibility into known issues and how to fix
                them.
              </Text>
            </ExpandableSection>
          </DataListItem>

          <DataListItem>
            <ExpandableSection
              toggleContent={
                <Flex>
                  <FlexItem>
                    <Icon size="lg" id="public-containers-dropdown">
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
              <Text id="public-containers-info">
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
          Quay.io is a managed container registry service provided by Red Hat to
          deliver secure storage, distribution, and governance of containers and
          cloud native artifacts on any infrastructure. It is also available as
          a self-managed product running standalone or on top of Red Hat
          Openshift.
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
