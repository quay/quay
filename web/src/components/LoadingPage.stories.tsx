import type {Meta, StoryObj} from '@storybook/react';
import {Button} from '@patternfly/react-core';
import {LoadingPage} from './LoadingPage';

const meta: Meta<typeof LoadingPage> = {
  component: LoadingPage,
  title: 'Components/LoadingPage',
};
export default meta;
type Story = StoryObj<typeof LoadingPage>;

export const Default: Story = {};

export const WithTitle: Story = {
  args: {
    title: 'Loading repositories...',
  },
};

export const WithMessage: Story = {
  args: {
    title: 'Loading',
    message: 'Fetching repository data from the registry.',
  },
};

export const WithActions: Story = {
  args: {
    title: 'Loading',
    message: 'This is taking longer than expected.',
    primaryAction: <Button variant="primary">Retry</Button>,
    secondaryActions: <Button variant="link">Cancel</Button>,
  },
};
