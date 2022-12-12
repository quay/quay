import {Grid, GridItem, Text, Title} from '@patternfly/react-core';
import {Button} from '@patternfly/react-core';
import {GenerateEncryptedPassword} from 'src/components/modals/GenerateEncryptedPasswordModal';
import {useState} from 'react';

export const CliConfiguration = () => {
  const [open, toggleOpen] = useState(false);
  return (
    <Grid hasGutter>
      <GridItem span={12}>
        <Title headingLevel="h3">Docker CLI Password</Title>
      </GridItem>
      <GridItem span={9}>
        <Text>
          The Docker CLI stores passwords entered on the command line in
          plaintext. It is therefore highly recommended to generate an encrypted
          version of your password for use with docker login.
        </Text>
      </GridItem>
      <GridItem span={6}>
        <Button variant="primary" onClick={() => toggleOpen(true)}>
          Generate encrypted password
        </Button>
      </GridItem>
      <GenerateEncryptedPassword
        modalOpen={open}
        title="Generate an encrypted password"
        buttonText="Generate"
        toggleModal={() => toggleOpen(false)}
      />
    </Grid>
  );
};
