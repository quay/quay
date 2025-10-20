import {
  Button,
  Card,
  CardBody,
  CardTitle,
  ClipboardCopy,
  Grid,
  GridItem,
  PageSection,
  PageSectionVariants,
  Skeleton,
  Text,
  TextArea,
  TextContent,
  TextVariants,
} from '@patternfly/react-core';
import {useEffect, useState} from 'react';
import {useMutation, useQueryClient} from '@tanstack/react-query';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {useQuayState} from 'src/hooks/UseQuayState';
import {RepositoryDetails} from 'src/resources/RepositoryResource';
import axios from 'src/libs/axios';
import {useAlerts} from 'src/hooks/UseAlerts';
import {AlertVariant} from 'src/atoms/AlertState';

interface InformationProps {
  organization: string;
  repository: string;
  repoDetails: RepositoryDetails;
}

async function updateRepositoryDescription(
  org: string,
  repo: string,
  description: string,
) {
  const response = await axios.put(`/api/v1/repository/${org}/${repo}`, {
    description,
  });
  return response.data;
}

export default function Information(props: InformationProps) {
  const {organization, repository, repoDetails} = props;
  const config = useQuayConfig();
  const {inReadOnlyMode} = useQuayState();
  const {addAlert} = useAlerts();
  const queryClient = useQueryClient();

  const [description, setDescription] = useState(
    repoDetails?.description || '',
  );
  const [isEditing, setIsEditing] = useState(false);

  // Sync description state with repoDetails when it changes
  useEffect(() => {
    setDescription(repoDetails?.description || '');
  }, [repoDetails?.description]);

  const updateDescriptionMutation = useMutation(
    async (newDescription: string) => {
      return await updateRepositoryDescription(
        organization,
        repository,
        newDescription,
      );
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries([
          'repodetails',
          organization,
          repository,
        ]);
        setIsEditing(false);
        addAlert({
          variant: AlertVariant.Success,
          title: 'Repository description updated successfully',
        });
      },
      onError: (error) => {
        addAlert({
          variant: AlertVariant.Failure,
          title: 'Failed to update repository description',
        });
        console.error('Error updating description:', error);
      },
    },
  );

  const handleDescriptionChange = (value: string) => {
    setDescription(value);
  };

  const handleSaveDescription = () => {
    updateDescriptionMutation.mutate(description);
  };

  const handleCancelEdit = () => {
    setDescription(repoDetails?.description || '');
    setIsEditing(false);
  };

  const serverHostname = config?.config?.SERVER_HOSTNAME || 'quay.io';
  const podmanPullCommand = `podman pull ${serverHostname}/${organization}/${repository}`;
  const dockerPullCommand = `docker pull ${serverHostname}/${organization}/${repository}`;

  return (
    <PageSection variant={PageSectionVariants.light}>
      <Grid hasGutter>
        {/* Repository Activity Placeholder */}
        <GridItem span={12} md={5}>
          <Card>
            <CardTitle>Repository Activity</CardTitle>
            <CardBody>
              <Skeleton height="200px" />
              <TextContent style={{marginTop: '1rem', textAlign: 'center'}}>
                <Text component={TextVariants.small}>
                  Activity heatmap coming soon
                </Text>
              </TextContent>
            </CardBody>
          </Card>
        </GridItem>

        {/* Pull Commands */}
        <GridItem span={12} md={7}>
          <Card>
            <CardTitle>Pull Commands</CardTitle>
            <CardBody>
              <Grid hasGutter>
                <GridItem span={12}>
                  <TextContent>
                    <Text component={TextVariants.small}>
                      Pull this container with the following Podman command:
                    </Text>
                  </TextContent>
                  <ClipboardCopy isReadOnly hoverTip="Copy" clickTip="Copied">
                    {podmanPullCommand}
                  </ClipboardCopy>
                </GridItem>
                <GridItem span={12}>
                  <TextContent>
                    <Text component={TextVariants.small}>
                      Pull this container with the following Docker command:
                    </Text>
                  </TextContent>
                  <ClipboardCopy isReadOnly hoverTip="Copy" clickTip="Copied">
                    {dockerPullCommand}
                  </ClipboardCopy>
                </GridItem>
              </Grid>
            </CardBody>
          </Card>
        </GridItem>

        {/* Repository Description */}
        <GridItem span={12}>
          <Card>
            <CardTitle>Description</CardTitle>
            <CardBody>
              {!isEditing && (
                <>
                  <TextContent>
                    <Text component={TextVariants.p}>
                      {description || 'No description provided'}
                    </Text>
                  </TextContent>
                  {repoDetails?.can_write && !inReadOnlyMode && (
                    <TextContent>
                      <Text
                        component={TextVariants.a}
                        onClick={() => setIsEditing(true)}
                        style={{cursor: 'pointer', marginTop: '1rem'}}
                      >
                        Edit description
                      </Text>
                    </TextContent>
                  )}
                </>
              )}
              {isEditing && (
                <>
                  <TextArea
                    value={description}
                    onChange={(_event, value) => handleDescriptionChange(value)}
                    rows={5}
                    aria-label="Repository description"
                    placeholder="Enter repository description..."
                  />
                  <div style={{marginTop: '1rem'}}>
                    <Button
                      variant="primary"
                      onClick={handleSaveDescription}
                      isLoading={updateDescriptionMutation.isLoading}
                      isDisabled={updateDescriptionMutation.isLoading}
                    >
                      Save
                    </Button>{' '}
                    <Button
                      variant="link"
                      onClick={handleCancelEdit}
                      isDisabled={updateDescriptionMutation.isLoading}
                    >
                      Cancel
                    </Button>
                  </div>
                </>
              )}
            </CardBody>
          </Card>
        </GridItem>
      </Grid>
    </PageSection>
  );
}
