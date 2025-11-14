import {
  PageSection,
  PageSectionVariants,
  Title,
  TextContent,
  Spinner,
  Card,
  CardBody,
} from '@patternfly/react-core';
import {ListIcon} from '@patternfly/react-icons';
import {QuayBreadcrumb} from 'src/components/breadcrumb/Breadcrumb';
import Empty from 'src/components/empty/Empty';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
import {useChangeLog} from 'src/hooks/UseChangeLog';
import {Navigate} from 'react-router-dom';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';

function ChangeLogHeader() {
  return (
    <>
      <QuayBreadcrumb />
      <PageSection variant={PageSectionVariants.light} hasShadowBottom>
        <div className="co-m-nav-title--row">
          <Title headingLevel="h1">Change Log</Title>
        </div>
      </PageSection>
    </>
  );
}

export default function ChangeLog() {
  const {isSuperUser, loading: userLoading} = useCurrentUser();
  const {
    changeLog,
    isLoading: changeLogLoading,
    error,
  } = useChangeLog();

  if (userLoading) {
    return null;
  }

  // Redirect non-superusers
  if (!isSuperUser) {
    return <Navigate to="/organization" replace />;
  }

  return (
    <>
      <ChangeLogHeader />
      <PageSection>
        {changeLogLoading ? (
          <div style={{textAlign: 'center', padding: '2rem'}}>
            <Spinner size="lg" />
          </div>
        ) : error && (error as Error)?.message !== 'Fresh login required' ? (
          <Empty
            title="Error Loading Change Log"
            icon={ListIcon}
            body="Cannot load change log. Please contact support."
          />
        ) : changeLog?.log ? (
          <Card>
            <CardBody>
              <TextContent>
                <Markdown
                  remarkPlugins={[remarkGfm]}
                  rehypePlugins={[rehypeRaw]}
                  components={{
                    // Customize headings to be larger like Angular version
                    // H2 is used for both main title AND version headers
                    h2: ({children}) => (
                      <Title
                        headingLevel="h2"
                        size="3xl"
                        style={{marginTop: '1.5rem', marginBottom: '1rem'}}
                      >
                        {children}
                      </Title>
                    ),
                    // H3 subsections (Api, Autoprune, etc.) use default markdown styling
                    // Customize links to open in new tab for external links
                    a: ({href, children, ...props}) => {
                      const isExternal = href?.startsWith('http');
                      return (
                        <a
                          {...props}
                          href={href}
                          target={isExternal ? '_blank' : undefined}
                          rel={isExternal ? 'noopener noreferrer' : undefined}
                        >
                          {children}
                        </a>
                      );
                    },
                  }}
                >
                  {changeLog.log}
                </Markdown>
              </TextContent>
            </CardBody>
          </Card>
        ) : (
          <Empty
            title="No Change Log Available"
            icon={ListIcon}
            body="Change log content is not available at this time."
          />
        )}
      </PageSection>
    </>
  );
}
