import {
  Dropdown,
  DropdownItem,
  KebabToggle,
  DropdownPosition,
} from '@patternfly/react-core';
import {useState} from 'react';
import {Link, useSearchParams} from 'react-router-dom';
import {AlertVariant} from 'src/atoms/AlertState';
import {useAlerts} from 'src/hooks/UseAlerts';
import {ITeams, useDeleteTeam} from 'src/hooks/UseTeams';
import {getTeamMemberPath} from 'src/routes/NavigationPath';

export default function TeamViewKebab(props: TeamViewKebabProps) {
  const [isKebabOpen, setIsKebabOpen] = useState<boolean>(false);
  const [searchParams] = useSearchParams();
  const {addAlert} = useAlerts();

  const {removeTeam} = useDeleteTeam({
    orgName: props.organizationName,
    onSuccess: () => {
      props.deSelectAll();
      addAlert({
        variant: AlertVariant.Success,
        title: `Successfully deleted team`,
      });
    },
    onError: (err) => {
      addAlert({
        variant: AlertVariant.Failure,
        title: `Failed to delete team: ${err}`,
      });
    },
  });

  return (
    <Dropdown
      onSelect={() => setIsKebabOpen(!isKebabOpen)}
      toggle={
        <KebabToggle
          data-testid={`${props.team.name}-toggle-kebab`}
          onToggle={() => {
            setIsKebabOpen(!isKebabOpen);
          }}
        />
      }
      isOpen={isKebabOpen}
      dropdownItems={[
        <DropdownItem
          key="link"
          component={
            <Link
              to={getTeamMemberPath(
                location.pathname,
                props.organizationName,
                props.team.name,
                searchParams.get('tab'),
              )}
              data-testid={`${props.team.name}-manage-team-member-option`}
            >
              Manage team members
            </Link>
          }
        ></DropdownItem>,
        <DropdownItem
          key="set-repo-perms"
          onClick={props.onSelectRepo}
          data-testid={`${props.team.name}-set-repo-perms-option`}
        >
          Set repository permissions
        </DropdownItem>,
        <DropdownItem
          key="delete"
          onClick={() => removeTeam(props.team)}
          className="red-color"
          data-testid={`${props.team.name}-del-option`}
        >
          Delete
        </DropdownItem>,
      ]}
      isPlain
      position={DropdownPosition.right}
    />
  );
}

interface TeamViewKebabProps {
  organizationName: string;
  team: ITeams;
  deSelectAll: () => void;
  onSelectRepo: () => void;
}
