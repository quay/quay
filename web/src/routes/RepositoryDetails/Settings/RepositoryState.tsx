import {
  Alert,
  Button,
  Form,
  FormGroup,
  Radio,
  Spinner,
} from '@patternfly/react-core';
import {AxiosError} from 'axios';
import {useEffect, useState} from 'react';
import {AlertVariant} from 'src/atoms/AlertState';
import {useAlerts} from 'src/hooks/UseAlerts';
import {useRepositoryState} from 'src/hooks/UseRepositoryState';
import {getDisplayError} from 'src/resources/ErrorHandling';
import {
  RepositoryState as IRepositoryState,
  RepositoryDetails,
} from 'src/resources/RepositoryResource';

export const RepositoryStateForm = (props: StateProps) => {
  const {addAlert} = useAlerts();
  const [selectedState, setSelectedState] = useState(props.repoDetails.state);
  const handleSubmit = (e) => {
    e.preventDefault();
    setState(selectedState as IRepositoryState);
  };

  const {
    setState,
    loadingSetRepositoryState,
    errorSetRepositoryState,
    errorSetRepositoryStateDetails,
  } = useRepositoryState(
    props.org,
    props.repo,
    props.repoDetails.state as IRepositoryState,
  );

  useEffect(() => {
    if (errorSetRepositoryState) {
      addAlert({
        title:
          'Failed to set repository state to ' +
          repoStateToString(selectedState as IRepositoryState),
        variant: AlertVariant.Failure,
        message: getDisplayError(errorSetRepositoryStateDetails as AxiosError),
      });
    }
  }, [errorSetRepositoryState]);

  const repoStateToString = (state: IRepositoryState) => {
    switch (state) {
      case 'NORMAL':
        return 'normal';
      case 'MIRROR':
        return 'mirror';
      case 'READ_ONLY':
        return 'read-only';
    }
  };

  if (loadingSetRepositoryState) {
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
