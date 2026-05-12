import type {Meta, StoryObj} from '@storybook/react';
import {fn} from '@storybook/test';
import {ConfirmationModal} from './ConfirmationModal';

const meta: Meta<typeof ConfirmationModal> = {
  component: ConfirmationModal,
  title: 'Components/Modals/ConfirmationModal',
};
export default meta;
type Story = StoryObj<typeof ConfirmationModal>;

export const Default: Story = {
  args: {
    title: 'Make repositories public?',
    description:
      'Are you sure you want to make the selected repositories public? This action will allow anyone to pull images from these repositories.',
    modalOpen: true,
    buttonText: 'Confirm',
    toggleModal: fn(),
    handleModalConfirm: fn(),
    selectedItems: [],
  },
};

export const Destructive: Story = {
  args: {
    title: 'Delete repositories?',
    description:
      'This action cannot be undone. All tags and images in the selected repositories will be permanently deleted.',
    modalOpen: true,
    buttonText: 'Delete',
    toggleModal: fn(),
    handleModalConfirm: fn(),
    selectedItems: ['org/repo-1', 'org/repo-2'],
  },
};

export const Closed: Story = {
  args: {
    title: 'Confirm action',
    description: 'This modal is closed.',
    modalOpen: false,
    buttonText: 'Confirm',
    toggleModal: fn(),
    handleModalConfirm: fn(),
    selectedItems: [],
  },
};
