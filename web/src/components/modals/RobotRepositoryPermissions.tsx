import {FormGroup, TextInput} from '@patternfly/react-core';
import React, {useState, useImperativeHandle, useEffect} from 'react';
import AddToRepository from './robotAccountWizard/AddToRepository';
import {IRepository} from 'src/resources/RepositoryResource';
import {IRobot} from 'src/resources/RobotsResource';
import {useRobotPermissions} from 'src/hooks/useRobotPermissions';
import {addDisplayError} from 'src/resources/ErrorHandling';
import {useRepositories} from 'src/hooks/UseRepositories';

export default function RobotRepositoryPermissions(
  props: RobotRepositoryPermissionsProps,
) {
  // Fetching repos
  const {repos: repos} = useRepositories(props.namespace);
  const [loading, setLoading] = useState<boolean>(true);
  const [robotPermissions, setRobotPermissions] = useState([]);
  const [err, setErr] = useState<string[]>();

  const resetRobotPermissions = () => {
    setRobotPermissions([]);
  };

  useImperativeHandle(props.robotPermissionsPlaceholder, () => {
    return {
      resetRobotPermissions: resetRobotPermissions,
    };
  });

  const {result} = useRobotPermissions({
    orgName: props.namespace,
    robName: props.robotAccount.name,
    onSuccess: (result) => {
      setLoading(false);
      setRobotPermissions(result);
    },
    onError: (err) => {
      setErr([addDisplayError('Unable to fetch robot accounts', err)]);
      setLoading(false);
    },
  });

  return (
    <>
      <FormGroup
        label="Provide a name for your robot account:"
        fieldId="robot-name"
        isRequired
        disabled
      >
        <TextInput
          value={props.robotAccount.name}
          type="text"
          aria-label="robot-name-value"
          isDisabled
          className="fit-content"
        />
      </FormGroup>
      <br />
      <FormGroup
        label="Description"
        fieldId="robot-description"
        disabled
        className="fit-content"
      >
        <TextInput
          value={props.robotAccount.description}
          type="text"
          aria-label="robot-description"
          isDisabled
        />
      </FormGroup>
      <br />
      <AddToRepository
        namespace={props.namespace}
        dropdownItems={props.RepoPermissionDropdownItems}
        repos={repos}
        selectedRepos={props.selectedRepos}
        setSelectedRepos={props.setSelectedRepos}
        selectedRepoPerms={props.selectedRepoPerms}
        setSelectedRepoPerms={props.setSelectedRepoPerms}
        robotPermissions={robotPermissions}
        wizardStep={false}
        robotName={props.robotAccount.name}
        fetchingRobotPerms={loading}
        setPrevRepoPerms={props.setPrevRepoPerms}
        setNewRepoPerms={props.setNewRepoPerms}
        setShowRepoModalSave={props.setShowRepoModalSave}
      />
    </>
  );
}

interface RobotRepositoryPermissionsProps {
  robotAccount: IRobot;
  namespace: string;
  RepoPermissionDropdownItems: any[];
  repos: IRepository[];
  selectedRepos: any[];
  setSelectedRepos: (repos) => void;
  selectedRepoPerms: any[];
  setSelectedRepoPerms: (repoPerm) => void;
  robotPermissionsPlaceholder: any;
  setPrevRepoPerms: (preVal) => void;
  setNewRepoPerms: (newVal) => void;
  setShowRepoModalSave: (boolean) => void;
}
