import {useEffect, useState} from 'react';
import {
  Dropdown,
  DropdownItem,
  DropdownList,
  MenuToggle,
  MenuToggleElement,
} from '@patternfly/react-core';
import EllipsisVIcon from '@patternfly/react-icons/dist/esm/icons/ellipsis-v-icon';
import {AlertVariant, useUI} from 'src/contexts/UIContext';
import {
  IOAuthApplication,
  useDeleteOAuthApplication,
} from 'src/hooks/UseOAuthApplications';
import DeleteModalForRowTemplate from 'src/components/modals/DeleteModalForRowTemplate';

export default function OAuthApplicationActionsKebab(
  props: OAuthApplicationDropdownProps,
) {
  const [isOpen, setIsOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const {addAlert} = useUI();

  const {
    removeOAuthApplication,
    errorDeleteOAuthApplication: error,
    successDeleteOAuthApplication: success,
  } = useDeleteOAuthApplication(props.orgName);

  useEffect(() => {
    if (error) {
      addAlert({
        variant: AlertVariant.Failure,
        title: `Error deleting oauth application: ${error}`,
      });
    }
  }, [error]);

  useEffect(() => {
    if (success) {
      addAlert({
        variant: AlertVariant.Success,
        title: `Successfully deleted oauth application: ${props.oauthApplication.name}`,
      });
    }
  }, [success]);

  const handleDeleteClick = () => {
    setIsOpen(false); // Close the dropdown
    setIsDeleteModalOpen(true); // Open confirmation modal
  };

  const handleConfirmDelete = () => {
    removeOAuthApplication({oauthApp: props.oauthApplication});
    setIsDeleteModalOpen(false);
  };

  return (
    <>
      <Dropdown
        onSelect={() => setIsOpen(!isOpen)}
        toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
          <MenuToggle
            ref={toggleRef}
            id={`${props.oauthApplication.name}-toggle-kebab`}
            data-testid="oauth-application-actions"
            variant="plain"
            onClick={() => setIsOpen(!isOpen)}
            isExpanded={isOpen}
          >
            <EllipsisVIcon />
          </MenuToggle>
        )}
        isOpen={isOpen}
        onOpenChange={(isOpen) => setIsOpen(isOpen)}
        shouldFocusToggleOnSelect
      >
        <DropdownList>
          <DropdownItem
            onClick={() => {
              setIsOpen(false);
              if (props.onEdit) {
                props.onEdit();
              }
            }}
            data-testid={`${props.oauthApplication.name}-edit-option`}
          >
            Edit
          </DropdownItem>
          <DropdownItem
            onClick={handleDeleteClick}
            data-testid={`${props.oauthApplication.name}-del-option`}
          >
            Delete
          </DropdownItem>
        </DropdownList>
      </Dropdown>

      <DeleteModalForRowTemplate
        deleteMsgTitle="Delete OAuth Application"
        isModalOpen={isDeleteModalOpen}
        toggleModal={() => setIsDeleteModalOpen(false)}
        deleteHandler={handleConfirmDelete}
        itemToBeDeleted={props.oauthApplication}
        keyToDisplay="name"
      />
    </>
  );
}

interface OAuthApplicationDropdownProps {
  orgName: string;
  oauthApplication: IOAuthApplication;
  onEdit?: () => void;
}
