import { Dropdown, DropdownItem, KebabToggle, DropdownPosition } from '@patternfly/react-core';
import { useState } from 'react';
import AddTagModal from './TagsActionsAddTagModal';
import EditLabelsModal from './TagsActionsLabelsModal';
import EditExpirationModal from './TagsActionsEditExpirationModal';

export default function TagActions(props: TagActionsProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [isAddTagModalOpen, setIsAddTagModalOpen] = useState(false);
    const [isEditLabelsModalOpen, setIsEditLabelsModalOpen] = useState(false);
    const [isEditExpirationModalOpen, setIsEditExpirationModalOpen] = useState(false);

    const dropdownItems = [
        <DropdownItem 
            key="add-tag-action"
            onClick={() => {
                setIsOpen(false);
                setIsAddTagModalOpen(true);
            }}
        >
            Add new tag
        </DropdownItem>,
        <DropdownItem 
            key="edit-labels-action"
            onClick={() => {
                setIsOpen(false);
                setIsEditLabelsModalOpen(true);
            }}
        >
            Edit labels
        </DropdownItem>,
        <DropdownItem 
            key="edit-expiration-action"
            onClick={() => {
                setIsOpen(false);
                setIsEditExpirationModalOpen(true);
            }}
        >
            Change expiration
        </DropdownItem>,
    ];
  
    return (
    <>
        <Dropdown
        toggle={<KebabToggle id="tag-actions-kebab" onToggle={(isOpen: boolean)=>setIsOpen(isOpen)} />}
        isOpen={isOpen}
        isPlain
        position={DropdownPosition.right}
        dropdownItems={dropdownItems}
        />
        <AddTagModal
            org={props.org}
            repo={props.repo}
            isOpen={isAddTagModalOpen}
            setIsOpen={setIsAddTagModalOpen}
            manifest={props.manifest}
            loadTags={props.loadTags}
        />
        <EditLabelsModal
            org={props.org}
            repo={props.repo}
            manifest={props.manifest}
            isOpen={isEditLabelsModalOpen}
            setIsOpen={setIsEditLabelsModalOpen}
        />
        <EditExpirationModal
            org={props.org}
            repo={props.repo}
            isOpen={isEditExpirationModalOpen}
            setIsOpen={setIsEditExpirationModalOpen}
            tags={props.tags}
            expiration={props.expiration}
            loadTags={props.loadTags}
        />
    </>
    );
}

interface TagActionsProps {
    org: string;
    repo: string;
    tags: string[];
    expiration: string;
    manifest: string;
    loadTags: () => void;
}
