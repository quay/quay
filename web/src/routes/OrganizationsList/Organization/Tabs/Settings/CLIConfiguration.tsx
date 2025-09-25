import {
  FlexItem,
  Title,
  Form,
  Flex,
  Button,
  Text,
  Spinner,
  Alert,
  EmptyState,
  EmptyStateIcon,
  EmptyStateBody,
  Divider,
  Dropdown,
  DropdownItem,
  DropdownList,
  MenuToggle,
} from '@patternfly/react-core';
import {Table, Thead, Tr, Th, Tbody, Td} from '@patternfly/react-table';
import {EllipsisVIcon, KeyIcon} from '@patternfly/react-icons';
import {GenerateEncryptedPassword} from 'src/components/modals/GenerateEncryptedPasswordModal';
import CreateApplicationTokenModal from 'src/components/modals/CreateApplicationTokenModal';
import RevokeTokenModal from 'src/components/modals/RevokeTokenModal';
import {useApplicationTokens} from 'src/hooks/UseApplicationTokens';
import {IApplicationToken} from 'src/resources/UserResource';
import {useState} from 'react';

export const CliConfiguration = () => {
  const [encryptedPasswordModalOpen, toggleEncryptedPasswordModal] =
    useState(false);
  const [createTokenModalOpen, setCreateTokenModalOpen] = useState(false);
  const [revokeTokenModalOpen, setRevokeTokenModalOpen] = useState(false);
  const [tokenToRevoke, setTokenToRevoke] = useState<IApplicationToken | null>(
    null,
  );
  const [dropdownOpen, setDropdownOpen] = useState<Record<string, boolean>>({});

  const {data: tokensData, isLoading, error} = useApplicationTokens();

  const handleRevokeToken = (token: IApplicationToken) => {
    setTokenToRevoke(token);
    setRevokeTokenModalOpen(true);
  };

  const handleCloseRevokeModal = () => {
    setRevokeTokenModalOpen(false);
    setTokenToRevoke(null);
  };

  const toggleDropdown = (tokenUuid: string) => {
    setDropdownOpen((prev) => ({
      ...prev,
      [tokenUuid]: !prev[tokenUuid],
    }));
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleDateString();
  };

  return (
    <Form id="cli-configuration-form" width="70%">
      {/* Docker CLI Password Section */}
      <Flex
        spaceItems={{default: 'spaceItemsSm'}}
        direction={{default: 'column'}}
      >
        <FlexItem>
          <Title headingLevel="h3" className="pf-v5-u-text-align-left">
            Docker CLI password
          </Title>
        </FlexItem>
        <FlexItem>
          The Docker CLI stores passwords entered on the command line in
          plaintext. It is highly recommended to generate an encrypted version
          of your password for use with docker login.
        </FlexItem>
      </Flex>
      <Flex width={'70%'}>
        <Button
          variant="secondary"
          onClick={() => toggleEncryptedPasswordModal(true)}
          id="cli-password-button"
        >
          Generate encrypted password
        </Button>
      </Flex>

      <Divider className="pf-v5-u-my-sm" />

      {/* Docker CLI and other Application Tokens Section */}
      <Flex
        spaceItems={{default: 'spaceItemsSm'}}
        direction={{default: 'column'}}
      >
        <FlexItem>
          <Title headingLevel="h3" className="pf-v5-u-text-align-left">
            Docker CLI and other Application Tokens
          </Title>
        </FlexItem>
        <FlexItem>
          As an alternative to using your password for Docker and rkt CLIs, an
          application token can be generated below.
        </FlexItem>
      </Flex>

      <Flex width={'70%'} className="pf-v5-u-mb-md">
        <Button
          variant="secondary"
          onClick={() => setCreateTokenModalOpen(true)}
          id="create-app-token-button"
        >
          Create application token
        </Button>
      </Flex>

      {/* Application Tokens Table */}
      {isLoading && (
        <div className="pf-v5-u-text-align-center pf-v5-u-p-lg">
          <Spinner size="md" />
          <Text className="pf-v5-u-mt-sm">Loading tokens...</Text>
        </div>
      )}

      {error && (
        <Alert variant="danger" isInline title="Error loading tokens">
          {(error as Error)?.message || 'Failed to load application tokens'}
        </Alert>
      )}

      {!isLoading && !error && tokensData?.tokens && (
        <>
          {tokensData.tokens.length === 0 ? (
            <EmptyState>
              <EmptyStateIcon icon={KeyIcon} />
              <Title headingLevel="h4" size="lg">
                No application tokens
              </Title>
              <EmptyStateBody>
                You haven&apos;t created any application tokens yet. Create one
                to use as an alternative to your password for CLI
                authentication.
              </EmptyStateBody>
            </EmptyState>
          ) : (
            <Table aria-label="Application tokens table" variant="compact">
              <Thead>
                <Tr>
                  <Th>Title</Th>
                  <Th>Last Accessed</Th>
                  <Th>Expiration</Th>
                  <Th>Created</Th>
                  <Th width={10}></Th>
                </Tr>
              </Thead>
              <Tbody>
                {tokensData.tokens.map((token) => (
                  <Tr key={token.uuid}>
                    <Td dataLabel="Title">{token.title}</Td>
                    <Td dataLabel="Last Accessed">
                      {formatDate(token.last_accessed)}
                    </Td>
                    <Td dataLabel="Expiration">
                      {formatDate(token.expiration)}
                    </Td>
                    <Td dataLabel="Created">{formatDate(token.created)}</Td>
                    <Td isActionCell>
                      <Dropdown
                        isOpen={dropdownOpen[token.uuid] || false}
                        onSelect={() =>
                          setDropdownOpen((prev) => ({
                            ...prev,
                            [token.uuid]: false,
                          }))
                        }
                        onOpenChange={(isOpen) =>
                          setDropdownOpen((prev) => ({
                            ...prev,
                            [token.uuid]: isOpen,
                          }))
                        }
                        toggle={(toggleRef) => (
                          <MenuToggle
                            ref={toggleRef}
                            aria-label={`Actions for ${token.title}`}
                            variant="plain"
                            onClick={() => toggleDropdown(token.uuid)}
                            isExpanded={dropdownOpen[token.uuid] || false}
                            data-testid="token-actions-dropdown"
                          >
                            <EllipsisVIcon />
                          </MenuToggle>
                        )}
                        shouldFocusToggleOnSelect
                        popperProps={{
                          position: 'right',
                          enableFlip: true,
                        }}
                      >
                        <DropdownList>
                          <DropdownItem
                            key="revoke"
                            onClick={() => handleRevokeToken(token)}
                          >
                            Revoke Token
                          </DropdownItem>
                        </DropdownList>
                      </Dropdown>
                    </Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          )}
        </>
      )}

      {/* Modals */}
      <GenerateEncryptedPassword
        modalOpen={encryptedPasswordModalOpen}
        title="Generate an encrypted password"
        buttonText="Generate"
        toggleModal={() => toggleEncryptedPasswordModal(false)}
      />

      <CreateApplicationTokenModal
        isOpen={createTokenModalOpen}
        onClose={() => setCreateTokenModalOpen(false)}
      />

      <RevokeTokenModal
        isOpen={revokeTokenModalOpen}
        onClose={handleCloseRevokeModal}
        token={tokenToRevoke}
      />
    </Form>
  );
};
