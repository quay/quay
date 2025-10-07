import React from 'react';
import {
  GithubIcon,
  GoogleIcon,
  GitlabIcon,
  ExternalLinkAltIcon,
} from '@patternfly/react-icons';

interface IconImageViewProps {
  value: string;
  className?: string;
}

// Get the appropriate PatternFly icon for a provider
const getProviderIcon = (providerId: string): React.ComponentType => {
  switch (providerId) {
    case 'github':
      return GithubIcon;
    case 'google':
      return GoogleIcon;
    case 'gitlab':
      return GitlabIcon;
    default:
      return ExternalLinkAltIcon;
  }
};

export function IconImageView({value, className = ''}: IconImageViewProps) {
  // Check if value is an image URL (contains '/')
  if (value.indexOf('/') >= 0) {
    return (
      <img
        src={value}
        className={`icon-image ${className}`}
        alt="Provider icon"
      />
    );
  }

  // Convert FontAwesome class to provider ID (e.g., "fa-github" → "github")
  const providerId = value.replace('fa-', '');

  // Get the appropriate icon component
  const IconComponent = getProviderIcon(providerId);

  return <IconComponent className={`icon-image ${className}`} />;
}
