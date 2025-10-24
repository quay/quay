import {Flex, FlexItem} from '@patternfly/react-core';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import './QuayFooter.css';

export function QuayFooter() {
  const quayConfig = useQuayConfig();

  const version = quayConfig?.version || '';
  const documentationRoot = quayConfig?.config?.DOCUMENTATION_ROOT || '';

  // Don't render footer if no content to display
  if (!version && !documentationRoot) {
    return null;
  }

  return (
    <footer className="quay-footer">
      <Flex>
        <FlexItem>
          {documentationRoot && (
            <a
              href={documentationRoot}
              target="_blank"
              rel="noopener noreferrer"
              className="quay-footer-link"
            >
              Documentation
            </a>
          )}
        </FlexItem>
        <FlexItem>
          {version && <span className="quay-footer-version">{version}</span>}
        </FlexItem>
      </Flex>
    </footer>
  );
}
