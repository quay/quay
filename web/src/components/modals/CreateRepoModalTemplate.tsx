import {useRef, useState} from 'react';
import {
  Modal,
  ModalVariant,
  Button,
  Form,
  FormGroup,
  TextInput,
  Radio,
  Flex,
  FlexItem,
  FormHelperText,
  HelperText,
  HelperTextItem,
  SelectOption,
  Select,
  SelectList,
  MenuToggle,
  MenuToggleElement,
} from '@patternfly/react-core';
import {IRepository} from 'src/resources/RepositoryResource';
import FormError from 'src/components/errors/FormError';
import {ExclamationCircleIcon} from '@patternfly/react-icons';
import {addDisplayError} from 'src/resources/ErrorHandling';
import {IOrganization} from 'src/resources/OrganizationResource';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {useCreateRepository} from 'src/hooks/UseCreateRepository';

enum visibilityType {
  PUBLIC = 'PUBLIC',
  PRIVATE = 'PRIVATE',
}

export default function CreateRepositoryModalTemplate(
  props: CreateRepositoryModalTemplateProps,
) {
  if (!props.isModalOpen) {
    return null;
  }
  const [err, setErr] = useState<string>();
  const quayConfig = useQuayConfig();

  const [currentOrganization, setCurrentOrganization] = useState({
    // For org scoped view, the name is set current org and for Repository list view,
    // the name is set to 1st value from the Namespace dropdown
    name: props.orgName
      ? props.orgName
      : props.username
      ? props.username
      : null,
    isDropdownOpen: false,
  });

  const {createRepository} = useCreateRepository({
    onSuccess: () => {
      props.handleModalToggle();
    },
    onError: (error) => {
      setErr(addDisplayError('Unable to create repository', error));
    },
  });

  const [validationState, setValidationState] = useState({
    repoName: true,
    namespace: true,
  });

  const [newRepository, setNewRepository] = useState({
    name: '',
    description: '',
  });

  const [repoVisibility, setrepoVisibility] = useState(visibilityType.PUBLIC);

  const nameInputRef = useRef();

  const handleNameInputChange = (
    _event: React.FormEvent<HTMLInputElement>,
    value,
  ) => {
    let regex = /^[a-z0-9][.a-z0-9_-]{0,254}$/;
    if (quayConfig?.features.EXTENDED_REPOSITORY_NAMES) {
      // Extended repostitory name regex: allows "/" in repo names
      regex = /^(?=.{0,255}$)[a-z0-9][.a-z0-9_-]*(?:\/[a-z0-9][.a-z0-9_-]*)*$/;
    }
    setValidationState({
      ...validationState,
      repoName: regex.test(value) && value.length < 256,
    });
    setNewRepository({...newRepository, name: value});
  };

  const handleRepoDescriptionChange = (value) => {
    setNewRepository({...newRepository, description: value});
  };

  const validateInput = () => {
    const validNamespace = !!currentOrganization.name;
    const validRepo = !!newRepository.name;
    setValidationState({repoName: validRepo, namespace: validNamespace});
    return validNamespace && validRepo;
  };

  const createRepositoryHandler = async () => {
    if (!validateInput()) {
      return;
    }
    await createRepository({
      namespace: currentOrganization.name,
      repository: newRepository.name,
      visibility: repoVisibility.toLowerCase(),
      description: newRepository.description,
      repo_kind: 'image',
    });
  };

  const handleNamespaceSelection = (e, value) => {
    setCurrentOrganization((prevState) => ({
      name: value,
      isDropdownOpen: !prevState.isDropdownOpen,
    }));
  };

  // namespace list includes both the orgs list and the user namespace
  const namespaceSelectionList = () => {
    const userSelection = (
      <SelectOption
        key={props.username}
        value={props.username}
        data-testid={`user-${props.username}`}
      >
        {props.username}
      </SelectOption>
    );
    const orgsSelectionList = props.organizations.map((orgs, idx) => (
      <SelectOption
        key={idx}
        value={orgs.name}
        data-testid={`org-${orgs.name}`}
      >
        {orgs.name}
      </SelectOption>
    ));

    return [userSelection, ...orgsSelectionList];
  };

  return (
    <Modal
      title="Create repository"
      id="create-repository-modal"
      variant={ModalVariant.large}
      isOpen={props.isModalOpen}
      onClose={props.handleModalToggle}
      actions={[
        <Button
          key="confirm"
          variant="primary"
          onClick={createRepositoryHandler}
          form="modal-with-form-form"
          isDisabled={
            !currentOrganization.name ||
            !newRepository.name ||
            !validationState.repoName
          }
        >
          Create
        </Button>,
        <Button key="cancel" variant="link" onClick={props.handleModalToggle}>
          Cancel
        </Button>,
      ]}
    >
      <FormError message={err} setErr={setErr} />
      <Form id="modal-with-form-form" maxWidth="765px">
        <Flex
          flexWrap={{default: 'nowrap'}}
          spaceItems={{default: 'spaceItemsMd'}}
        >
          <FlexItem>
            <FormGroup
              isInline
              label="Namespace"
              fieldId="modal-with-form-form-name"
              isRequired
            >
              <Flex
                flexWrap={{default: 'nowrap'}}
                spaceItems={{default: 'spaceItemsMd'}}
              >
                <FlexItem>
                  <Select
                    aria-label="Namespace select"
                    isOpen={currentOrganization.isDropdownOpen}
                    selected={currentOrganization.name || 'Select namespace'}
                    onSelect={handleNamespaceSelection}
                    toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
                      <MenuToggle
                        ref={toggleRef}
                        onClick={() =>
                          setCurrentOrganization((prevState) => ({
                            ...prevState,
                            isDropdownOpen: !prevState.isDropdownOpen,
                          }))
                        }
                        isExpanded={currentOrganization.isDropdownOpen}
                        isDisabled={props.orgName !== null}
                        data-testid="selected-namespace-dropdown"
                      >
                        {currentOrganization.name}
                      </MenuToggle>
                    )}
                    shouldFocusToggleOnSelect
                  >
                    <SelectList>{namespaceSelectionList()}</SelectList>
                  </Select>
                </FlexItem>
                <FlexItem>/</FlexItem>
              </Flex>

              {!validationState.namespace && (
                <FormHelperText>
                  <HelperText>
                    <HelperTextItem
                      variant="error"
                      icon={<ExclamationCircleIcon />}
                    >
                      Select a namespace
                    </HelperTextItem>
                  </HelperText>
                </FormHelperText>
              )}
            </FormGroup>
          </FlexItem>
          <FlexItem>
            <FormGroup
              label="Repository name"
              isRequired
              fieldId="modal-with-form-form-name"
            >
              <TextInput
                isRequired
                type="text"
                id="repository-name-input"
                value={newRepository.name}
                onChange={handleNameInputChange}
                ref={nameInputRef}
                validated={validationState.repoName ? 'default' : 'error'}
              />

              {!validationState.repoName && (
                <FormHelperText>
                  <HelperText>
                    <HelperTextItem
                      variant="error"
                      icon={<ExclamationCircleIcon />}
                    >
                      Must contain only lowercase alphanumeric and _-
                      characters. Max 255 characters.
                    </HelperTextItem>
                  </HelperText>
                </FormHelperText>
              )}
            </FormGroup>
          </FlexItem>
        </Flex>
        <FormGroup
          label="Repository description"
          fieldId="modal-with-form-form-email"
        >
          <TextInput
            type="text"
            id="repository-description-input"
            name="modal-with-form-form-name"
            value={newRepository.description}
            onChange={(_event, value) => handleRepoDescriptionChange(value)}
            ref={nameInputRef}
          />
        </FormGroup>
        <FormGroup
          label="Repository visibility"
          fieldId="modal-with-form-form-email"
        >
          <Flex
            direction={{default: 'column'}}
            spaceItems={{default: 'spaceItemsMd'}}
          >
            <Radio
              isChecked={repoVisibility === visibilityType.PUBLIC}
              name="Public"
              onChange={() => setrepoVisibility(visibilityType.PUBLIC)}
              label="Public"
              id={visibilityType.PUBLIC}
              value={visibilityType.PUBLIC}
              description="Anyone can see and pull from this repository. You choose who can push."
            />
            <Radio
              isChecked={repoVisibility === visibilityType.PRIVATE}
              name="Private"
              onChange={() => setrepoVisibility(visibilityType.PRIVATE)}
              label="Private"
              id={visibilityType.PRIVATE}
              value={visibilityType.PRIVATE}
              description="You choose who can see,pull and push from/to this repository."
            />
          </Flex>
        </FormGroup>
      </Form>
    </Modal>
  );
}

interface CreateRepositoryModalTemplateProps {
  isModalOpen: boolean;
  handleModalToggle?: () => void;
  orgName?: string;
  updateListHandler: (value: IRepository) => void;
  username: string;
  organizations: IOrganization[];
}
