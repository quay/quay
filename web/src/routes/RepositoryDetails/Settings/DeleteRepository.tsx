import {
  Alert,
  AlertActionCloseButton,
  Button,
  Modal,
  ModalVariant,
  TextInput,
} from '@patternfly/react-core';
import {useState} from 'react';
import {useNavigate} from 'react-router-dom';
import Conditional from 'src/components/empty/Conditional';
import {useDeleteRepositories} from 'src/hooks/UseDeleteRepositories';

export default function DeleteRepository({org, repo}: DeleteRepositoryProps) {
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [repoNameInput, setRepoNameInput] = useState<string>('');
  const [isError, setIsError] = useState<boolean>(false);
  const navigate = useNavigate();
  const {deleteRepositories} = useDeleteRepositories({
    onSuccess: () => {
      navigate('/repository');
    },
    onError: () => {
      setIsError(true);
    },
  });

  return (
    <>
      <Modal
        variant={ModalVariant.small}
        title="Delete Repository?"
        id="delete-repository-modal"
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        actions={[
          <Button
            key="confirm"
            variant="danger"
            isDisabled={`${org}/${repo}` != repoNameInput}
            onClick={() => deleteRepositories([{namespace: org, name: repo}])}
          >
            Delete
          </Button>,
          <Button
            key="cancel"
            variant="link"
            onClick={() => {
              setIsModalOpen(!isModalOpen);
            }}
          >
            Cancel
          </Button>,
        ]}
      >
        <Conditional if={isError}>
          <Alert
            isInline
            variant="danger"
            title="Unable to delete repository"
            actionClose={
              <AlertActionCloseButton onClose={() => setIsError(false)} />
            }
          />
        </Conditional>
        <Alert
          isInline
          variant="danger"
          title={`You are requesting to delete the repository ${org}/${repo}. This action is non-reversable.`}
          style={{marginBottom: '1em'}}
        />
        <div>
          You must type {org}/{repo} below to confirm deletion:
        </div>
        <TextInput
          value={repoNameInput}
          type="text"
          onChange={(value) => setRepoNameInput(value.trim())}
          aria-label="repo-delete-name-input"
          placeholder="Enter repository here"
        />
      </Modal>
      <Alert
        isInline
        variant="danger"
        title="Deleting a repository cannot be undone. Here be dragons!"
        style={{marginBottom: '1em'}}
      />
      <Button variant="danger" onClick={() => setIsModalOpen(true)}>
        Delete Repository
      </Button>
    </>
  );
}

interface DeleteRepositoryProps {
  org: string;
  repo: string;
}
