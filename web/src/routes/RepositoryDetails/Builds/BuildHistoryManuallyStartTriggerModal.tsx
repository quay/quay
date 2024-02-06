import {
  Alert,
  Button,
  HelperText,
  HelperTextItem,
  Modal,
  ModalVariant,
  Spinner,
  TextInput,
  Title,
} from '@patternfly/react-core';
import {RepositoryBuildTrigger, SourceRef} from 'src/resources/BuildResource';
import BuildTriggerDescription from './BuildTriggerDescription';
import Conditional from 'src/components/empty/Conditional';
import {useState} from 'react';
import {useStartBuild} from 'src/hooks/UseBuilds';
import {useAlerts} from 'src/hooks/UseAlerts';
import {AlertVariant} from 'src/atoms/AlertState';
import {useSourceRefs} from 'src/hooks/UseBuildTriggers';
import TypeAheadSelect from 'src/components/TypeAheadSelect';
import {isNullOrUndefined} from 'src/libs/utils';

export default function ManuallyStartTrigger(props: ManuallyStartTriggerProps) {
  const {trigger, org, repo} = props;
  const [commit, setCommit] = useState<string>('');
  const [ref, setRef] = useState<SourceRef>({name: '', kind: null});
  const [isValid, setIsValid] = useState<boolean>(false);
  const {addAlert} = useAlerts();
  const {refs, isLoading, isError, error} = useSourceRefs(
    org,
    repo,
    trigger?.id,
    null,
    trigger.service !== 'custom-git',
  );
  const {startBuild} = useStartBuild(org, repo, trigger?.id, {
    onSuccess: (data) => {
      addAlert({
        title: `Build started successfully with ID ${data.id}`,
        variant: AlertVariant.Success,
      });
      props.onClose();
    },
    onError: (error) => {
      addAlert({
        title: 'Failed to start build',
        variant: AlertVariant.Failure,
        message: error.message,
      });
    },
  });

  const onChange = (value: string) => {
    setIsValid(/^[A-Fa-f0-9]{7,}$/.test(value));
    setCommit(value);
  };

  const onRefChange = (value: string) => {
    const foundRef = refs?.find((ref) => ref.name === value);
    if (isNullOrUndefined(foundRef)) {
      setIsValid(false);
      setRef({name: value, kind: null});
    } else {
      setIsValid(true);
      setRef(foundRef);
    }
  };

  return (
    <Modal
      id="manually-start-build-modal"
      isOpen={props.isOpen}
      aria-label="Manually Start Build"
      onClose={() => props.onClose()}
      variant={ModalVariant.medium}
      actions={[
        <Button
          key="start-build"
          isDisabled={!isValid}
          onClick={() =>
            startBuild(trigger?.service === 'custom-git' ? commit : ref)
          }
        >
          Start Build
        </Button>,
        <Button key="cancel" variant="primary" onClick={() => props.onClose()}>
          Cancel
        </Button>,
      ]}
      style={{
        overflowX: 'visible',
        overflowY: 'visible',
      }}
    >
      <Conditional if={trigger?.service === 'custom-git'}>
        <Title headingLevel="h4">Manually Start Build Trigger</Title>
        <BuildTriggerDescription trigger={trigger} />
        <br />
        Commit:
        <TextInput
          id="manual-build-commit-input"
          value={commit}
          onChange={(_, value) => onChange(value)}
          type="text"
          pattern="^([A-Fa-f0-9]{7,})$"
          placeholder="1c002dd"
        />
        <Conditional if={!isValid && commit !== ''}>
          <HelperText id="helper-text">
            <HelperTextItem variant="error">
              Invalid commit pattern
            </HelperTextItem>
          </HelperText>
        </Conditional>
      </Conditional>
      <Conditional if={trigger?.service !== 'custom-git'}>
        <Conditional if={isLoading}>
          <Spinner />
        </Conditional>
        <Conditional if={isError}>
          <Alert variant="danger" title={error?.toString()} />
        </Conditional>
        <Conditional if={!isLoading && !isError}>
          <Title headingLevel="h4">Manually Start Build Trigger</Title>
          <BuildTriggerDescription trigger={trigger} />
          <br />
          Branch/Tag:{' '}
          <TypeAheadSelect
            value={ref.name}
            onChange={(value) => onRefChange(value)}
            initialSelectOptions={refs?.map((ref, index) => ({
              key: `${ref.kind}/${ref.name}`,
              onClick: () => setRef(ref),
              id: `ref-option-${index}`,
              value: ref.name,
            }))}
          />
          <Conditional if={!isValid && ref?.name !== ''}>
            <HelperText id="helper-text">
              <HelperTextItem variant="error">
                Branch/Tag not found
              </HelperTextItem>
            </HelperText>
          </Conditional>
        </Conditional>
      </Conditional>
    </Modal>
  );
}

interface ManuallyStartTriggerProps {
  org: string;
  repo: string;
  isOpen: boolean;
  onClose: () => void;
  trigger: RepositoryBuildTrigger;
}
