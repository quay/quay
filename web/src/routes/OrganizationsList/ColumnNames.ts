import type {ColumnConfig} from 'src/components/ManageColumns';

const ColumnNames = {
  name: 'Name',
  adminEmail: 'Admin Email',
  repoCount: 'Repo Count',
  teamsCount: 'Teams',
  membersCount: 'Members',
  robotsCount: 'Robots',
  lastModified: 'Last Modified',
  size: 'Size',
  options: 'Settings',
};

/**
 * Default column configurations for the Organizations List table.
 * Note: Some columns have additional visibility controlled by feature flags
 * (MAILING, QUOTA_MANAGEMENT, EDIT_QUOTA) and user permissions (isSuperUser)
 * in OrganizationsList.tsx and OrganizationsListTableData.tsx
 */
export const organizationDefaultColumns: ColumnConfig[] = [
  {
    id: 'name',
    title: ColumnNames.name,
    isVisible: true,
    isDefault: true,
    isDisabled: true, // Name column cannot be hidden
    sortIndex: 0,
  },
  {
    id: 'adminEmail',
    title: ColumnNames.adminEmail,
    isVisible: true,
    isDefault: true, // Default for superusers when MAILING feature enabled
    sortIndex: 1,
  },
  {
    id: 'repoCount',
    title: ColumnNames.repoCount,
    isVisible: true,
    isDefault: true,
    sortIndex: 2,
  },
  {
    id: 'teamsCount',
    title: ColumnNames.teamsCount,
    isVisible: true,
    isDefault: true,
    sortIndex: 3,
  },
  {
    id: 'membersCount',
    title: ColumnNames.membersCount,
    isVisible: true,
    isDefault: true,
    sortIndex: 4,
  },
  {
    id: 'robotsCount',
    title: ColumnNames.robotsCount,
    isVisible: true,
    isDefault: true,
    sortIndex: 5,
  },
  {
    id: 'lastModified',
    title: ColumnNames.lastModified,
    isVisible: true,
    isDefault: true,
    sortIndex: 6,
  },
  {
    id: 'size',
    title: ColumnNames.size,
    isVisible: true,
    isDefault: false, // Additional column (requires QUOTA_MANAGEMENT + EDIT_QUOTA)
    sortIndex: 7,
  },
  {
    id: 'options',
    title: ColumnNames.options,
    isVisible: true,
    isDefault: true, // Default for superusers
    sortIndex: 8,
  },
];

export default ColumnNames;
