import {UsersIcon, UserIcon, CogIcon} from '@patternfly/react-icons';
import {MemberType} from 'src/resources/RepositoryResource';
import Conditional from './empty/Conditional';

export default function EntityIcon(props: EntityProps) {
  switch (props.type) {
    case MemberType.team:
      return (
        <>
          <Conditional
            if={props.includeIcon != null ? props.includeIcon : true}
          >
            <UsersIcon />
          </Conditional>{' '}
          <Conditional if={props.includeText}>Team</Conditional>{' '}
          <Conditional if={props.name != null}>{props.name}</Conditional>
        </>
      );
    case MemberType.robot:
      return (
        <>
          <Conditional
            if={props.includeIcon != null ? props.includeIcon : true}
          >
            <CogIcon />
          </Conditional>{' '}
          <Conditional if={props.includeText}>Robot</Conditional>{' '}
          <Conditional if={props.name != null}>{props.name}</Conditional>
        </>
      );
    case MemberType.user:
      return (
        <>
          <Conditional
            if={props.includeIcon != null ? props.includeIcon : true}
          >
            <UserIcon />
          </Conditional>{' '}
          <Conditional if={props.includeText}>User</Conditional>{' '}
          <Conditional if={props.name != null}>{props.name}</Conditional>
        </>
      );
  }
}

interface EntityProps {
  type: MemberType;
  name?: string;
  includeIcon?: boolean;
  includeText?: boolean;
}
