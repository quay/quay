import {FlexItem, Title, Form, Flex} from '@patternfly/react-core';
import {Button} from '@patternfly/react-core';
import {GenerateEncryptedPassword} from 'src/components/modals/GenerateEncryptedPasswordModal';
import {useState} from 'react';

export const CliConfiguration = () => {
  const [open, toggleOpen] = useState(false);
  return (
    <Form id="form-form" width="70%">
      <Flex
        spaceItems={{default: 'spaceItemsSm'}}
        direction={{default: 'column'}}
      >
        <FlexItem>
          <Title headingLevel="h3">Docker CLI password</Title>
        </FlexItem>
        <FlexItem>
          {`The Docker CLI stores passwords entered on the command line in
            plaintext.`}
        </FlexItem>
        <FlexItem>
          {`It is therefore highly recommended to generate an
            encrypted version of your password for use with docker login.`}
        </FlexItem>
      </Flex>
      <Flex width={'70%'}>
        <Button
          variant="secondary"
          onClick={() => toggleOpen(true)}
          id="cli-password-button"
        >
          Generate encrypted password
        </Button>
      </Flex>
      <GenerateEncryptedPassword
        modalOpen={open}
        title="Generate an encrypted password"
        buttonText="Generate"
        toggleModal={() => toggleOpen(false)}
      />
    </Form>
  );
};
