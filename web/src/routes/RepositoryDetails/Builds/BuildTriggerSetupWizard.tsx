import {Wizard, WizardHeader, WizardStep} from '@patternfly/react-core';
import {useState} from 'react';
import {
  GitNamespace,
  RepositoryBuildTrigger,
  TriggerConfig,
} from 'src/resources/BuildResource';
import RepositoryStep from './BuildTriggerSetupWizardRepository';
import TaggingOptionsStep from './BuildTriggerSetupWizardTaggingOptions';
import DockerfileStep from './BuildTriggerSetupWizardDockerfile';
import ContextStep from './BuildTriggerSetupWizardContext';
import RobotAccounts from './BuildTriggerSetupWizardRobotAccounts';
import ReviewAndFinishProps from './BuildTriggerSetupWizardReviewAndFinish';
import {useActivateBuildTrigger} from 'src/hooks/UseBuildTriggers';
import {useAlerts} from 'src/hooks/UseAlerts';
import {AlertVariant} from 'src/atoms/AlertState';
import SelectOrganization from './BuildTriggerSetupWizardOrganization';
import {isNullOrUndefined} from 'src/libs/utils';
import HostedRepository from './BuildTriggerSetupWizardHostedRepository';
import TriggerOptions from './BuildTriggerSetupWizardTriggerOptions';
import {useSourceDirs} from 'src/hooks/UseBuildTriggers';

export default function BuildTriggerSetupWizard(
  props: BuildTriggerSetupWizardProps,
) {
  const [gitNamespace, setGitNamespace] = useState<GitNamespace>(null);
  const [repoUrl, setRepoUrl] = useState<string>('');
  const [repoUrlValid, setRepoUrlValid] = useState<boolean>(false);
  const [branchTagFilter, setBranchTagFilter] = useState<string>(null);
  const [hasBranchTagFilter, setHasBranchTagFilter] = useState<boolean>(false);
  const [tagTemplates, setTagTemplates] = useState<string[]>([]);
  const [tagWithBranchOrTag, setTagWithBranchOrTag] = useState(false);
  const [addLatestTag, setAddLatestTag] = useState(false);
  const [dockerfilePath, setDockerfilePath] = useState<string>('');
  const [dockerPathValid, setDockerPathValid] = useState<boolean>(false);
  const [contextPath, setContextPath] = useState<string>('');
  const [contextPathValid, setContextPathValid] = useState<boolean>(false);
  const [selectedRobot, setSelectedRobot] = useState<string>(null);
  const [robotAccountValid, setRobotAccountValid] = useState<boolean>(false);
  const isCustomGit = props.trigger.service === 'custom-git';
  const sourceDirsRequest = useSourceDirs(
    props.org,
    props.repo,
    props.trigger.id,
    repoUrl,
    !isNullOrUndefined(repoUrl) && repoUrl !== '' && !isCustomGit,
  );
  const {addAlert} = useAlerts();
  const {activateTrigger} = useActivateBuildTrigger(
    props.org,
    props.repo,
    props.trigger.id,
    {
      onSuccess: (data: RepositoryBuildTrigger) => {
        props.setUpdatedTrigger(data);
      },
      onError: (error) => {
        const message =
          error?.response?.data?.error_message || error.toString();
        addAlert({
          title: 'Error activating trigger',
          message: message,
          variant: AlertVariant.Failure,
        });
      },
    },
  );

  const activate = () => {
    const config: TriggerConfig = {
      buildSource: repoUrl,
      tagTemplates: tagTemplates,
      defaultTagFromRef: tagWithBranchOrTag,
      latestForDefaultBranch: addLatestTag,
      dockerfilePath: dockerfilePath,
      context: contextPath,
    };
    activateTrigger({config: config, robot: selectedRobot});
  };

  const customGitSteps = [
    <WizardStep
      name="Enter Repository"
      id="enter-repository"
      key="enter-repository"
      isHidden={!isCustomGit}
      footer={{isNextDisabled: !repoUrlValid, cancelButtonText: ''}}
    >
      <RepositoryStep
        repoUrl={repoUrl}
        setRepoUrl={setRepoUrl}
        setRepoUrlValid={setRepoUrlValid}
        repoUrlValid={repoUrlValid}
      />
    </WizardStep>,
  ];

  const hostedGitSteps = [
    <WizardStep
      name="Select Organization"
      id="select-organization"
      key="select-organization"
      isHidden={isCustomGit}
      footer={{isNextDisabled: isNullOrUndefined(gitNamespace)}}
    >
      <SelectOrganization
        org={props.org}
        repo={props.repo}
        triggerUuid={props.trigger.id}
        gitNamespace={gitNamespace}
        setGitNamespace={setGitNamespace}
        service={props.trigger.service}
      />
    </WizardStep>,
    <WizardStep
      name="Select Repository"
      id="enter-hosted-repository"
      key="enter-hosted-repository"
      isHidden={isCustomGit}
      footer={{
        isNextDisabled: repoUrl === '' || isNullOrUndefined(repoUrl),
        cancelButtonText: '',
      }}
    >
      <HostedRepository
        org={props.org}
        repo={props.repo}
        triggerUuid={props.trigger.id}
        repoUrl={repoUrl}
        setRepoUrl={setRepoUrl}
        gitNamespace={gitNamespace}
        service={props.trigger.service}
      />
    </WizardStep>,
    <WizardStep
      name="Configure Trigger"
      id="configure-trigger"
      key="configure-trigger"
      isHidden={isCustomGit}
    >
      <TriggerOptions
        org={props.org}
        repo={props.repo}
        triggerUuid={props.trigger.id}
        repoUrl={repoUrl}
        gitNamespace={gitNamespace}
        branchTagFilter={branchTagFilter}
        setBranchTagFilter={setBranchTagFilter}
        hasBranchTagFilter={hasBranchTagFilter}
        setHasBranchTagFilter={setHasBranchTagFilter}
      />
    </WizardStep>,
  ];

  return (
    <Wizard
      height={600}
      width={1170}
      isVisitRequired
      header={
        <WizardHeader
          onClose={props.onClose}
          title={`Setup Build Trigger: ${props.trigger.id.substring(0, 8)}`}
        />
      }
    >
      {isCustomGit ? customGitSteps : hostedGitSteps}
      <WizardStep
        name="Tagging Options"
        id="tagging-options"
        key="tagging-options"
        footer={{
          isNextDisabled: !tagWithBranchOrTag && tagTemplates.length === 0,
          cancelButtonText: '',
        }}
      >
        <TaggingOptionsStep
          tagWithBranchOrTag={tagWithBranchOrTag}
          setTagWithBranchOrTag={setTagWithBranchOrTag}
          addLatestTag={addLatestTag}
          setAddLatestTag={setAddLatestTag}
          tagTemplates={tagTemplates}
          setTagTemplates={setTagTemplates}
        />
      </WizardStep>
      <WizardStep
        name="Select Dockerfile"
        id="select-dockerfile"
        key="select-dockerfile"
        footer={{isNextDisabled: !dockerPathValid, cancelButtonText: ''}}
      >
        <DockerfileStep
          org={props.org}
          repo={props.repo}
          triggerUuid={props.trigger.id}
          buildSource={repoUrl}
          dockerfilePath={dockerfilePath}
          setDockerfilePath={setDockerfilePath}
          isCustomGit={isCustomGit}
          setDockerPathValid={setDockerPathValid}
          {...sourceDirsRequest}
        />
      </WizardStep>
      <WizardStep
        name="Select Context"
        id="select-context"
        key="select-context"
        footer={{isNextDisabled: !contextPathValid, cancelButtonText: ''}}
      >
        <ContextStep
          org={props.org}
          repo={props.repo}
          triggerUuid={props.trigger.id}
          buildSource={repoUrl}
          dockerfilePath={dockerfilePath}
          contextPath={contextPath}
          setContextPath={setContextPath}
          isCustomGit={isCustomGit}
          setContextPathValid={setContextPathValid}
          {...sourceDirsRequest}
        />
      </WizardStep>
      <WizardStep
        name="Robot Accounts"
        id="robot-accounts"
        key="robot-accounts"
        footer={{isNextDisabled: !robotAccountValid, cancelButtonText: ''}}
      >
        <RobotAccounts
          namespace={props.org}
          repo={props.repo}
          triggerUuid={props.trigger.id}
          dockerfilePath={dockerfilePath}
          contextPath={contextPath}
          buildSource={repoUrl}
          isOrganization={props.isOrganization}
          robotAccount={selectedRobot}
          setRobotAccount={setSelectedRobot}
          setRobotAccountValid={setRobotAccountValid}
        />
      </WizardStep>
      <WizardStep
        name="Review and Finish"
        id="review-and-finish"
        key="review-and-finish"
        footer={{
          nextButtonText: 'Finish',
          onNext: activate,
          cancelButtonText: '',
        }}
      >
        <ReviewAndFinishProps
          repoUrl={repoUrl}
          tagTemplates={tagTemplates}
          tagWithBranchOrTag={tagWithBranchOrTag}
          addLatestTag={addLatestTag}
          dockerfilePath={dockerfilePath}
          contextPath={contextPath}
          robotAccount={selectedRobot}
        />
      </WizardStep>
    </Wizard>
  );
}

interface BuildTriggerSetupWizardProps {
  org: string;
  repo: string;
  isOpen: boolean;
  trigger: RepositoryBuildTrigger;
  onClose: () => void;
  isOrganization: boolean;
  setUpdatedTrigger: (trigger: RepositoryBuildTrigger) => void;
}
