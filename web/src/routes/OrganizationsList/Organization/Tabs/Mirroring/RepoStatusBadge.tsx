import {Label} from '@patternfly/react-core';
import {
  CheckCircleIcon,
  ExclamationCircleIcon,
  InfoCircleIcon,
  InProgressIcon,
  MinusCircleIcon,
} from '@patternfly/react-icons';

export type RepoStatus =
  | 'DISCOVERED'
  | 'PENDING_SYNC'
  | 'CREATED'
  | 'SKIPPED'
  | 'FAILED';

interface RepoStatusBadgeProps {
  status: string;
}

interface StatusConfig {
  label: string;
  color: 'green' | 'red' | 'blue' | 'orange' | 'grey' | 'purple';
  icon: React.ReactNode;
}

const statusConfigs: Record<string, StatusConfig> = {
  DISCOVERED: {
    label: 'Discovered',
    color: 'blue',
    icon: <InfoCircleIcon />,
  },
  PENDING_SYNC: {
    label: 'Pending Sync',
    color: 'orange',
    icon: <InProgressIcon />,
  },
  CREATED: {
    label: 'Created',
    color: 'green',
    icon: <CheckCircleIcon />,
  },
  SKIPPED: {
    label: 'Skipped',
    color: 'grey',
    icon: <MinusCircleIcon />,
  },
  FAILED: {
    label: 'Failed',
    color: 'red',
    icon: <ExclamationCircleIcon />,
  },
};

export default function RepoStatusBadge({status}: RepoStatusBadgeProps) {
  const config = statusConfigs[status] || {
    label: status,
    color: 'grey' as const,
    icon: <InfoCircleIcon />,
  };

  return (
    <Label
      color={config.color}
      icon={config.icon}
      data-testid={`repo-status-badge-${status.toLowerCase()}`}
    >
      {config.label}
    </Label>
  );
}
