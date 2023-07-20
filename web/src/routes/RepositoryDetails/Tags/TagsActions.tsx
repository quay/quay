import { Dropdown, DropdownItem, KebabToggle } from '@patternfly/react-core';
import { useState } from 'react';
import AddTagModal from './TagsActionsAddTagModal';

export default function TagActions(props: TagActionsProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [isAddTagModalOpen, setIsAddTagModalOpen] = useState(false);

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
    </>
    );
}

interface TagActionsProps {
    org: string;
    repo: string;
    manifest: string;
    loadTags: () => void;
}
