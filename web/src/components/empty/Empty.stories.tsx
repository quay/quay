import type {Meta, StoryObj} from '@storybook/react';
import {CubesIcon, SearchIcon} from '@patternfly/react-icons';
import {Button} from '@patternfly/react-core';
import Empty from './Empty';

const meta: Meta<typeof Empty> = {
  component: Empty,
  title: 'Components/Empty/Empty',
};
export default meta;
type Story = StoryObj<typeof Empty>;

export const Default: Story = {
  args: {
    icon: CubesIcon,
    title: 'No repositories found',
    body: 'There are no repositories in this organization yet.',
  },
};

export const WithButton: Story = {
  args: {
    icon: CubesIcon,
    title: 'No repositories found',
    body: 'Create a repository to get started.',
    button: <Button variant="primary">Create Repository</Button>,
  },
};

export const SearchEmpty: Story = {
  args: {
    icon: SearchIcon,
    title: 'No results found',
    body: 'No results match the filter criteria. Clear all filters and try again.',
    button: <Button variant="link">Clear all filters</Button>,
  },
};
