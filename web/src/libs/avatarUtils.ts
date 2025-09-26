import {IAvatar} from 'src/resources/OrganizationResource';

// Color palette similar to the one used in Angular version
const AVATAR_COLORS = [
  '#969696',
  '#aec7e8',
  '#ff7f0e',
  '#ffbb78',
  '#2ca02c',
  '#98df8a',
  '#d62728',
  '#ff9896',
  '#9467bd',
  '#c5b0d5',
  '#8c564b',
  '#c49c94',
  '#e377c2',
  '#f7b6d2',
  '#7f7f7f',
  '#c7c7c7',
  '#bcbd22',
  '#1f77b4',
  '#17becf',
  '#9edae5',
];

/**
 * Generate a simple avatar from a namespace name
 * This creates a consistent avatar for any namespace without API calls
 */
export function generateAvatarFromName(name: string): IAvatar {
  // Simple hash function to get consistent color for same name
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    const char = name.charCodeAt(i);
    hash = (hash << 5) - hash + char;
    hash = hash & hash; // Convert to 32-bit integer
  }

  const colorIndex = Math.abs(hash) % AVATAR_COLORS.length;
  const color = AVATAR_COLORS[colorIndex];

  return {
    name: name,
    hash: Math.abs(hash).toString(),
    color: color,
    kind: 'generated', // Mark as generated locally
  };
}
