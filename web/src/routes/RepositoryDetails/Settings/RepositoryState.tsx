import {Spinner, Radio, Alert} from '@patternfly/react-core';
import {useRepositoryState} from 'src/hooks/UseRepositoryState';
import {
  RepositoryDetails,
  RepositoryState as IRepositoryState,
} from 'src/resources/RepositoryResource';
import {useState} from 'react';
import {Form, FormGroup, Button} from '@patternfly/react-core';

export const RepositoryStateForm = (props: StateProps) => {
  const [selectedState, setSelectedState] = useState(props.repoDetails.state);
  const handleSubmit = (e) => {
    e.preventDefault();
    setState(selectedState as IRepositoryState);
  };

  const {setState, loading: loadingSetState} = useRepositoryState(
    props.org,
    props.repo,
    props.repoDetails.state as IRepositoryState,
  );

  if (loadingSetState) {
    return <Spinner size="md" />;
  }

  return (
    <Form onSubmit={handleSubmit}>
      <FormGroup fieldId="repository-state">
        <Radio
          isChecked={selectedState === 'NORMAL'}
          name="repoState"
          onChange={() => setSelectedState('NORMAL' as IRepositoryState)}
          label="Normal"
          id="normal"
          value="normal"
          description="The repository will be in its standard operational state."
        />
        <br />
        <Radio
          isChecked={selectedState === 'MIRROR'}
          name="repoState"
          onChange={() => setSelectedState('MIRROR' as IRepositoryState)}
          label="Mirror"
          id="mirror"
          value="mirror"
          description="Mirror an entire repository or selectively limit which images are synced. When a repository is set as mirrored, you cannot manually add other images to that repository."
        />
        <br />
        <Radio
          isChecked={selectedState === 'READ_ONLY'}
          name="repoState"
          onChange={() => setSelectedState('READ_ONLY' as IRepositoryState)}
          label="Read Only"
          id="readonly"
          value="readonly"
          description="The repository will be in a read-only state."
        />
        {selectedState === 'READ_ONLY' && (
          <>
            <br />
            <Alert
              isInline
              variant="warning"
              title=" WARNING: This will prevent all pushes to the repository."
            />
            <br />
          </>
        )}
        <br />
        <Button
          type="submit"
          variant="primary"
          size="sm"
          isDisabled={selectedState === props.repoDetails.state}
        >
          Submit
        </Button>
      </FormGroup>
    </Form>
  );
};

interface StateProps {
  org: string;
  repo: string;
  repoDetails: RepositoryDetails;
}
