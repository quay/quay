import type {ColumnConfig} from 'src/components/ManageColumns';

export const RepositoryListColumnNames = {
  name: 'Name',
  visibility: 'Visibility',
  size: 'Size',
  lastModified: 'Last Modified',
};

/**
 * Default column configurations for the Repository List table.
 * Note: The 'size' column visibility is also controlled by feature flags
 * (QUOTA_MANAGEMENT && EDIT_QUOTA) in RepositoriesList.tsx
 */
export const repositoryDefaultColumns: ColumnConfig[] = [
  {
    id: 'name',
    title: RepositoryListColumnNames.name,
    isVisible: true,
    isDefault: true,
    isDisabled: true, // Name column cannot be hidden
    sortIndex: 0,
  },
  {
    id: 'visibility',
    title: RepositoryListColumnNames.visibility,
    isVisible: true,
    isDefault: true,
    sortIndex: 1,
  },
  {
    id: 'size',
    title: RepositoryListColumnNames.size,
    isVisible: true,
    isDefault: false, // Size is an additional column (requires feature flags)
    sortIndex: 2,
  },
  {
    id: 'lastModified',
    title: RepositoryListColumnNames.lastModified,
    isVisible: true,
    isDefault: true,
    sortIndex: 3,
  },
];

export const RobotAccountColumnNames = {
  robotAccountName: 'Robot account name',
  teams: 'Teams',
  repositories: 'Repositories',
  created: 'Created',
  lastAccessed: 'Last accessed',
};
