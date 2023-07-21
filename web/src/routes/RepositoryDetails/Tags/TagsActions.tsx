import { Dropdown, DropdownItem, KebabToggle } from '@patternfly/react-core';
import { useState } from 'react';
import AddTagModal from './TagsActionsAddTagModal';
import EditLabelsModal from './TagsActionsLabelsModal';

export default function TagActions(props: TagActionsProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [isAddTagModalOpen, setIsAddTagModalOpen] = useState(false);
    const [isEditLabelsModalOpen, setIsEditLabelsModalOpen] = useState(false);

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
    ];
  
    return (
    <>
        <Dropdown
        toggle={<KebabToggle id="tag-actions-kebab" onToggle={(isOpen: boolean)=>setIsOpen(isOpen)} />}
        isOpen={isOpen}
        isPlain
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
    </>
    );
}

interface TagActionsProps {
    org: string;
    repo: string;
    manifest: string;
    loadTags: () => void;
}
